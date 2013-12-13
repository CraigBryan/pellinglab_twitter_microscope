from production_files import utils
from cv2 import imwrite, VideoCapture #@UnresolvedImport
import datetime
from production_files.logger import Logger
from serial import Serial, SerialException
from serial.tools import list_ports
from time import sleep

'''
Created Oct 2, 2013

@author Craig Bryan

The interface with the arduino board. This includes the lighting, camera
movement and any other communication with the arduino board. Is also the
interface with the actual camera.

Note:
This implementation is currently blocking. Nothing will happen in the main
program until the arduino board returns a value.
'''

default_dict = {'arduino_port' : 'None',
                'max_x' : 1000,
                'max_y' : 1000,
                'max_z' : 1000}

class CameraCommunicator(object):
    """
    The interface between the CameraReciever and the BoardCommunicator, 
    Lights, Camera, and CameraPosition objects.
    
    Attributes:
        _lights: An instance of Lights that controls and tracks the state of the lights
        _camera_positions: The list of positions the samples being monitored.
        _board_comm: The communication interface with the Arduino board.
        cam: An instance of Camera that is the interface with the physical camera.
    """
    
    def __init__(self, hasCamera = True):
        """
        Read the initialization dictionary for this class and initialize
        the board connection, camera connection, sample positions, and light
        states.
        """
        
        config_dict = utils.read_config_dict("CameraCommunicator")
        self._lights = None
        self._camera_positions = None
        
        #Initialization of board comm
        try:
            port = config_dict['arduino_port']
        except KeyError:
            port = default_dict['arduino_port']
        
        self._board_comm = self._connect(port)
        
        #Initialization of the Camera
        if hasCamera:
            self.cam = Camera(config_dict['camera_number'])
        
        #Initialization of the Lights
        try:
            self._lights = Lights(self._board_comm, 
                                  config_dict['light_states'])
        except KeyError:
            self._lights = Lights(self._board_comm)
        
        #Initialization of the CameraPosition
        try:
            max_x = config_dict['max_x']
        except KeyError:
            max_x = default_dict['max_x']
        
        try:
            max_y = config_dict['max_y']
        except KeyError:
            max_y = default_dict['max_y']
            
        try:
            max_z = config_dict['max_z']
        except KeyError:
            max_z = default_dict['max_z']
            
        self._camera_positions = CameraPosition(self._board_comm, max_x, max_y, 
                                              max_z)
        
        #Set the sample positions
        self.sample_positions = []
        
        self._set_sample_pos(config_dict)
        
    
    def get_sample_image(self, sample_num):
        """
        Retrieve an image of the specified sample by organizing the movement,
        lighting, and board communication.
        
        Args:
            sample_num: The sample being imaged.
        
        Returns:
            A tuple of the form timestamp, image. The timestamp is the date and
            time the image was taken. The image a string with the filename of
            the newly saved image.
        """
        
        #Uses sample_num - 1 to translate from the 1-indexed twitter interface
        #to the 0-indexed Arduino interface 
        self._camera_positions.move(self.sample_positions[sample_num - 1])
        self._lights.on(sample_num - 1)
        
        timestamp, image = self.cam.get_image()
        
        self._lights.all_off()
        
        #Homes after every image capture, to reduce camera drift.
        self._camera_positions.home()
        
        return timestamp, image
    
    def get_camera_position_tracker(self):
        
        return self._camera_positions
    
    def get_lights_tracker(self):
        
        return self._lights
    
    def get_position_and_lights_trackers(self):
        
        return self.get_camera_position_tracker(), self.get_lights_tracker()
        
    def cleanup(self):
        """
        Close the connection with the Arduino to allow new connections to be
        made with it.
        """
        
        self._board_comm._connection.close()
        del self._board_comm
        
    def _set_sample_pos(self, config_dict):
        """
        Helper method for initializing the calibrated sample positions.
        Called in the __init__ of the CameraCommunicator
        """
        
        counter = 0;
        current_sample = []
        
        #Trim the dictionary to only samples
        for key in sorted(
                       {k: config_dict[k] for k in config_dict if '~s' in k}
                       ):
            
            current_sample.append(config_dict[key])
            if counter == 2:
                self.sample_positions.append((current_sample[0],
                                              current_sample[1],
                                              current_sample[2]))
                current_sample = []
                counter = 0
                
            else: 
                counter += 1
    
    def _connect(self, port):
        """
        Helper method that creates and initializes the board communicator. Pass
        the new board communicator to the objects that need to communicate
        with the Arduino, if necessary.
        """
        
        connection = BoardCommunicator(port)
        
        if self._camera_positions is not None:
            self._camera_positions.reset()
            self._camera_positions._board_comm = connection
        if self._lights is not None:
            self._lights.reset()
            self._lights._board_comm = connection
        
        return connection
    
class Camera(object):
    """
    The class responsible for communicating with the actual camera and
    getting images from it.
    
    Attributes:
        cam: An instance of an openCV VideoCapture. 
    """
    
    def __init__(self, device_num):
        """
        Uses a device num in case the system has multiple cameras attached.
        """
        
        self.cam = VideoCapture(device_num) 
        
    def get_image(self):
        """
        Grab a frame from the camera. The cameraCommunicator is the caller,
        and is responsible for lighting and location. The filename of the
        image is returned. 
        
        Raises:
            FatalCameraException: An image was not taken successfully.
        """
        
        #create the systematic filename
        timestamp = datetime.datetime.now()
        filename = utils.get_image_dir() + str(timestamp.date()) + \
                    str(timestamp.hour) + str(timestamp.minute) + \
                    str(timestamp.second) + '.jpg'
        
        #A series of reads to allow the camera to adjust to lighting
        self.cam.read()
        self.cam.read()
        self.cam.read()
        self.cam.read()
        
        #only the last is saved
        success, image = self.cam.read()
        
        if not success:
            raise FatalCameraException()
        else:
            imwrite(filename, image)
            
        return timestamp, filename

class BoardCommunicator(object):
    """
    Class actually responsible for the serial communication with the board.
    Needs to keep a running connection with the board, and reconnect if
    necessary. Reconnection will reboot the arduino, so homing is required.
    
    Attributes:
        _connection: The serial connection with the Arduino board.
        _logger: An Arduino-communication specific logger. Logs messages to and
                 from the Arduino board.
    """
    
    def __init__(self, port):
        """
        Connect to the Arduino board and create a logger to track communication.
        
        Args:
            Port: The stored port to attempt to connect to.
            
        Raises:
            SerialException: Unable to connect to the board.
        """
        
        self._logger = Logger(name = "arduino_log")
        self._connection = None
        self._establish_connection(port)
    
    def send(self, message):
        """
        Send a message to the Arduino board.
        
        Args:
            message: the string to be sent to the Arduino over the serial connection
            
        Returns:
            An integer specifying the success or error of sending the message to the
            Arduino board.
            
        Raises:
            SerialException: the connection to the Arduino board has been closed
        """
        
        self._logger.log("Sent to arduino: '%s'" %message)
        
        if self._connection.isOpen():
            self._connection.flushInput()
            self._connection.flushOutput()
            self._connection.write(message)
        else:
            raise SerialException("Connection to arduino board closed")
        
        #blocking waiting for feedback
        while(self._connection.inWaiting() == 0):
            pass
        
        sleep(1)        #allows for the entire message to be transmitted
        
        result = int(self._connection.read(self._connection.inWaiting()).rstrip())
        
        self._logger.log("Received from arduino: '%d'" %result)
        
        return result
        
    def _establish_connection(self, port):
        """
        Helper method to be used by the BoardCommunicator only to connect to the
        arduino board. Tells the arduino to home upon connection.
        """
        
        cxn = Serial()
        cxn.baudrate = 115200
        
        self._logger.log("Connecting to arduino board at %s" %port)
        cxn.port = port
        
        #Attempt to connect at the previously stored port.
        try:
            cxn.open()
        except (SerialException, OSError):
            cxn.close()
            self._logger.log("Failed connection to stored port %s" %port)
            
        if cxn.isOpen():
            sleep(3)
            
            while cxn.inWaiting() > 0:
                cxn.read()
            
            #Send the handshake message
            cxn.write("connection")
            sleep(3)
            msg = cxn.read(cxn.inWaiting()).strip()
            
            self._logger.log("Handshake string received from arduino: %r" %msg)
            
            if msg == "main":
                self._logger.log("Main Arduino control unit found at port %s"
                                  %port)
                self._connection = cxn
                
                if self.send("h") == 0:
                    self._logger.log("Homing of camera successful")
                    return
                else: 
                    self._logger.log("Homing failed upon connection")
                    raise SerialException("Homing Error, please check machine")
                
            else:
                self._logger.log("Connection at port %s was not the Arduino" +
                                 " control unit")
                cxn.close()
        
        #If the stored port fails, search available ports, trying the handshake
        #at each one
        else:
            self._logger.log("Searching available ports for the Arduino "
                             "control unit")
            cxn.close()
            
            for searched_port in list_ports.comports():
                cxn.port = searched_port[0]
                
                try:
                    cxn.open()
                except (SerialException, OSError):
                    self._logger.log("Failed connection to searched port %s" 
                                     %searched_port[0])
            
                if cxn.isOpen():
                    sleep(3)
                    
                    while cxn.inWaiting() > 0:
                        cxn.read()
                        
                    cxn.write("connection")
                    sleep(3)
                    msg = cxn.read(cxn.inWaiting()).strip()
                    
                    self._logger.log("Handshake string received from arduino: %r" %msg)
                    
                    if msg == "main":
                        self._logger.log("Main Arduino control unit found at port %s"
                                         %searched_port[0])
                        self._connection = cxn
                        utils.update_config_dict("CameraCommunicator", 
                                            dict(arduino_port = searched_port[0]))

                        if self.send("h") == 0:
                            self._logger.log("Homing of camera successful")
                            return
                        else: 
                            self._logger.log("Homing failed upon connection")
                            raise SerialException("Homing Error, please check machine")
                    
                    else:
                        self._logger.log(("Connection at port %s was not the Arduino" +
                                         " control unit") %searched_port[0])
                        cxn.close()
                        
        if self._connection is None:
            self._logger.log("Did not connect to the Arduino Board after " +
                                                        "searching all ports")
            raise SerialException("Did not connect to the Arduino Board")
                    
class Lights(object):
    """
    This represents the state of the lights.
    The state is represented by a list of boolean values.
    This class is responsible for sending the light-related messages to
    the board communicator. Is hard-coded to deal with up to 12 lights.
    
    Attributes:
        _board_comm: The communication interface with the Arduino board.
        _light_states: A list of on/off state for each individual light.
    """
    
    def __init__(self, board_comm, list_of_states = None):
        
        self._board_comm = board_comm
        
        if list_of_states is None:
            self._light_states = [False, False, False, False, False, False,
                                  False, False, False, False, False, False]
        else:
            self._light_states = list_of_states

    def on(self, light_num):
        """
        Turn on a light.
        
        Args:
            light_num: The light to turn on.
            
        Returns:
            The resulting message from the Arduino board.
        """
        
        if self._light_states[light_num] == False:
            result = self._board_comm.send("l i %s" %light_num)
            
            if result == 0:
                self._light_states[light_num] = True
            
            return result
        
    def off(self, light_num):
        """
        Turn on a light.
        
        Args:
            light_num: The light to turn off.
            
        Returns:
            The resulting message from the Arduino board.
        """
        
        if self._light_states[light_num] == True:
            result = self._board_comm.send("l o %s" %light_num)
            
            if result == 0:
                self._light_states[light_num] = False
            
            return result
        
    def all_off(self):
        """
        Turn off all the lights.
        
        Returns:
            The resulting message from the Arduino board.
        """
        
        result = self._board_comm.send("l o")
        
        self.list_of_states = [False, False, False, False, False, False,
                               False, False, False, False, False, False]
    
        return result
    
    def cascade(self):
        """
        Turn off all lights, then blink each light in order.
        
        Returns:
            The resulting message from the Arduino board.
        """
        
        result = self._board_comm.send("l c")
        
        self.all_off()
        self.list_of_states = [False, False, False, False, False, False,
                               False, False, False, False, False, False]
        
        return result
        
    def reset(self):
        """
        Called on board reconnection. Sets the light states to all False
        """
        
        self.list_of_states = [False, False, False, False, False, False,
                               False, False, False, False, False, False]

class CameraPosition(object):
    """
    This is a representation of the camera holder in the incubator. Ensures no 
    order causes the camera to move past its bounds, and keeps track of its 
    position. This class is responsible for sending the camera movement-related 
    commands to the board communicator.
    
    Attributes:
        max_x: The maximum x coordinate the camera can move to.
        max_y: The maximum y coordinate the camera can move to.
        max_z: The maximum z coordinate the camera can move to.
        cur_x: The current x coordinate of the camera.
        cur_y: The current y coordinate of the camera.
        cur_z: The current z coordinate of the camera.
        _board_comm: The communication interface with the Arduino board.
    """
    
    def __init__(self, board_comm, max_x, max_y, max_z, cur_x = 0, cur_y = 0, 
                 cur_z = 0):
        
        self._max_x = max_x
        self._max_y = max_y
        self._max_z = max_z
        self._cur_x = cur_x
        self._cur_y = cur_y
        self._cur_z = cur_z
        
        self._board_comm = board_comm
        
    def move(self, coords):
        """
        Check the camera move order and update the camera position if
        it is valid. Return true if successful, otherwise returns false.
        
        Args:
            coords: A tuple of the form (x, y, z) to move to.
        
        Raises:
            FatalCameraException: An error has occurred, and detected by an error
                message from the Arduino board.
        """
        
        x, y, z = coords
            
        result = self._board_comm.send("m a %s %s %s" %(str(x), str(y), str(z)))
        
        if result == 0:
            self._cur_x = x
            self._cur_y = y
            self._cur_z = z
        
        #Some program/microcontroller out of sync error
        elif result >= 21:
            #fixes by homing
            self.home()
        
        #Another error that may be caused by a host of things.
        else:
            #safest is to restart the whole program using an uncaught error
            raise FatalCameraException()
        
        return result 
    
    def relative_move(self, coords):
        """
        Takes relative coordinates and transform them to absolute so the 
        move command can handle them properly. Return true if successful,
        otherwise returns false.
        
        Args:
            coords: A tuple of the form (x, y, z) to move to.
        """
        
        x, y, z = coords
        
        x += self._cur_x;
        y += self._cur_y;
        z += self._cur_z;
        
        return self.move((x, y, z))
    
    def home(self):
        """
        Move the camera carriage to the home position, which is (0, 0, 0).
        
        Raises:
            FatalCameraException: An error has occurred, and detected by an error
                message from the Arduino board.
        """
        
        result = self._board_comm.send("h")
        
        if result == 0:
            self._cur_x = 0
            self._cur_y = 0
            self._cur_z = 0
        
        else:
            raise FatalCameraException()
        
        return result
        
    def get_position(self):
        """
        Returns:
            A tuple containing the current position of the camera.
        """
        
        return (self._cur_x, self._cur_y, self._cur_z)
    
    def reset(self):
        """
        Reset the camera position data to home.
        """
        
        self._cur_x = 0
        self._cur_y = 0
        self._cur_z = 0
        
class FatalCameraException(Exception):
    pass

class CameraMovementException(Exception):
    
    def __init__(self, message):
        self._message = message
        
    def __str__(self):
        return "Camera error: %s" %self._message
