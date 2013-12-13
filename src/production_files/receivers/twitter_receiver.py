'''
Created on Sep 6, 2013

@author: Craig Bryan
'''

from receiver import Receiver
from collections import deque
import twitter
import time
from production_files import utils

class TwitterReceiver(Receiver):
    """
    A receiver that pulls from and posts to Twitter
        
    Attributes:
        router: A reference to the router object that sends transactions and takes 
                transaction requests.
        r_id: The id that the router uses to route transactions to this receiver.
        twitter: A TwitterCommunicator instance.
    """        
    
    def __init__(self, router, r_id):
        """
        This creates an instance of the TwitterCommunicator class, that facilitates the
        communication with Twitter.
            
        Args:
            router: A reference to the router that this receiver is associated with.
            r_id: The string that the router refers to this receiver with.
        """
        
        super(TwitterReceiver, self).__init__(router, r_id)
        
        self.twitter = TwitterCommunicator()
        
    def process_transaction(self, transaction):
        """
        Attempts to process an incoming transaction, is called by the router object.
            
        Args:
            transaction: A reference to a transaction object.
            
        Commands:
            update: Pulls new tweets from twitter
            post: Posts a status message to twitter, or directly to a twitter user
        """
        
        if transaction.command == "update":
        
            #tells the twitter_communicator to post a tweet waiting in a queue
            self.twitter.post()
            
            #then pulls tweets
            self.twitter.pull_tweets() 
            
            #each tweet in the resulting queue is turned into a transaction
            tweets = self.twitter.retrieve_tweets()
            while len(tweets) > 0:
                content, user = tweets.popleft()
                
                #tweets are routed to the translator
                self.router.create_transaction(origin = user, 
                                               to_id = "translator", 
                                               command = "parse", 
                                               command_args = content)
                                          
            #this process is not logged, as logging this overloads the logging file
            transaction.process(success = True, finished = True, allow_log = False) 
            
        elif transaction.command == "post": 
        
            if transaction.origin == "twitter":
                #post an undirected tweet
                self.twitter.post(transaction.command_args)
            else:
                #otherwise a reply-to user is supplied, and a reply is sent
                self.twitter.reply(transaction.command_args, transaction.origin) 
                
            transaction.process(success = True, finished = True)
           
        else:
            transaction.log(info = "Unknown command passed to twitter receiver: %s"
                                    % transaction.command)

class TwitterCommunicator(object):
    """ 
    This handles communication between the program interfacing with the microscope and
    twitter. It allows for posting to the twitter account, replying to a user,
    and it pulls tweets that mention the lab account. This reads twitter auth from
    a config file. 
    
    To avoid hitting the twitter rate limits, the action of pulling incoming 
    tweets is throttled to once every 60 seconds, and the action of posting
    to twitter is throttled to once every 5 seconds. 
    
    Attributes:
        api: The wrapper for communicating with the Twitter API.
        screen_name: The username of the twitter account this is associated with.
        tweet_queue: A queue that contains all tweets pulled from the twitter feed.
        get_delay_time: The time required between requests to the Twitter API for
            new tweets to the account.
        post_delay_time: The time required between requests to the Twitter API to
            post new tweets.
        get_request_time: The time in seconds that the last request for new tweets
            to the Twitter API was made.
        post_request_time: The time in seconds that the last request to post new
            tweets to the Twitter API was made.
        id_file_name: The filename of the file that holds the ID of the last tweet
            processed.
    """
    
    def __init__(self, delay_time = [60, 5], last_id = None, 
                 id_file_name = "default_id_file.txt", 
                 twitter_auth_name = "Auth@cbrya_labtest"):
        """ 
        The initialization currently currently defaults to the @cbrya_labtest twitter
        oAuth credentials. It also initializes the various queues, times, and
        id-related variables.
        
        Args:
            delay_time: A list of the delay times needed. The first two are used.
            last_id: The tweet ID of the last processed tweet.
            id_file_name: The name of the file that stores the persistent ID 
                of the last tweet processed. 
            twitter_auth_name: The header name of the configuration entry that
                contains the authorization.
        """
        
        #Get the auth dictionary
        try:
            auth_dict = utils.read_config_dict(twitter_auth_name)
        
        #In case of failure, defaults to @cbrya_labtest
        except utils.BadConfigFileError:
            auth_dict = utils.read_config_dict("TwitterCommunicator")
        
        # The API object that will do the interaction with Twitter
        self.api = twitter.Api(auth_dict['con_key'], #@UndefinedVariable
                              auth_dict['con_sec_key'], 
                              auth_dict['acc_tkn'],  
                              auth_dict['acc_tkn_sec'])
        
        #This twitter accounts screen name. Stored to stay within twitter rate
        #limits.
        self.screen_name = self.api.VerifyCredentials().GetScreenName()
        
        #A queue to hold the unprocessed tweets             
        self.tweet_queue = deque()
        
        #A queue to hold the unsent twitter posts
        self.post_queue = deque()
        
        #Integer time delays to prevent getting rate limited
        self.get_delay_time = delay_time[0] #defaults to 60s (15 requests/15 min)
        self.post_delay_time = delay_time[1] #defaults to 5s (180 requests/15 min)
        
        #A time (in seconds) that will measure the time since the previous get
        #request from twitter
        self.get_request_time = time.time()
        
        #A time (in seconds) that will measure the time since the previous post
        #request from twitter
        self.post_request_time = time.time()
        
        #The filename of the file that holds the last twitter status processed
        self.id_file_name = id_file_name
        
        #The id of the last twitter status processed
        if(last_id == None):
            self.last_id = self._retrieve_last_id()
        else:
            self.last_id = last_id

    def pull_tweets(self):
        """
        Appends the list of new twitter statuses to the object's queue of unprocessed
        tweets, from the tweet with last_id. This is regulated to only occur maximum of
        once every delay_time.
        """
        if self._check_get_time():
   
            # Get tweets from twitter
            new_mentions = self.api.GetMentions(since_id=self.last_id)
            
            #update the last tweet id
            if len(new_mentions) > 0:
                tweet_id = new_mentions[0].GetId()
                #this if condition should always be true, but just to be safe
                if tweet_id > self.last_id:
                
                    # update the instance's last_id, and update the id file
                    self.last_id = tweet_id
                    self._store_last_id(self.last_id)
            
            # Add the new tweets to the queue, in the proper order
            self.tweet_queue.extend(reversed(new_mentions))
            
            self.get_request_time = time.time() #update the interaction time          
                
    def post(self, content = None):
        """ 
        This posts to twitter. If content for a tweet is given, then that content is
        appended to the queue for outgoing tweets. Then, if enough time has passed since
        the last API call to twitter, then the tweet at the front of the queue is sent
        """
        # add the tweet to the queue
        if content != None:
            self.post_queue.append(self._timestamp() + content)
        
        # post to twitter
        if self._check_post_time() and len(self.post_queue) > 0:
            to_post = self.post_queue.popleft()
            if len(to_post) > 140:
                to_post = self._tweet_split(to_post)
                
            self.api.PostUpdate(to_post) #post to twitter
                
            self.post_request_time = time.time() #update the interaction time
            
        
    def reply(self, content = None, user = None):
        """ 
        A simple method for replying to a specific user. Appends the user name to the
        content of the tweet and then uses the post method. Compares the username
        given to the name of the account this program uses, to avoid self-replies.
        
        Args:
            content: The text of the outgoing tweet.
            user: The username of the user this tweet is being directed to.
        """
        
        # make sure the account does not reply to itself, to avoid infinite tweeting loops
        if(self.screen_name != user):
        
            # Just a call to the post method, with the @user_id concatenated to the front
            self.post("@" + user + " " + content)
        else:
            print("self reply suppressed")
        
    def retrieve_tweets(self): 
        """ 
        This returns a queue of tuples of the form (tweet text, twitter status object).
        This is used for the processing of the tweets by the remainder of the program.
        The last_id file is also updated in this method, as it is assumed that once
        the tweets are taken from here, they are processed and thus they can be skipped
        in subsequent tweet pulls.
        
        Returns:
            A queue of tuples of tweet entries. Each tuple has the form: 
            (content, user).
        """
        
        # Queue to hold the tuples
        tweet_content = deque()
        
        # While there are new tweets to process
        while len(self.tweet_queue) > 0:
            # get the front tweet
            tweet = self.tweet_queue.popleft()
            
            # add the tweet information to the queue that will be returned
            tweet_content.append((tweet.GetText(), tweet.GetUser().GetScreenName()))
        
        # return the queue
        return tweet_content 
       
    #Reused time checks to prevent making too many requests to the twitter API
    def _check_get_time(self):
        return (time.time() - self.get_request_time > self.get_delay_time)    
        
    def _check_post_time(self):
        return (time.time() - self.post_request_time > self.post_delay_time) 
        
    # a method for loading the id of the last twitter message processed
    def _retrieve_last_id(self): 
        try:
            id_file = open(self.id_file_name, "r")
        except IOError:
            twitter_id = 0
        else:
            twitter_id = id_file.readline()
            id_file.close()
        return int(twitter_id)
        
    # a method for storing the id of the last twitter message processed
    def _store_last_id(self, twitter_id): 
        id_file = open(self.id_file_name, "w")
        id_file.write(str(twitter_id))
        id_file.close()
        
    # a method that returns the current timestamp
    def _timestamp(self):
        current = time.localtime()
        day = "%02d" % current.tm_mday
        month = "%02d" % current.tm_mon
        year = "%02d" % current.tm_year
        hours = "%02d" % current.tm_hour
        minutes = "%02d" % current.tm_min
        seconds = "%02d" % current.tm_sec
        date = ''.join([day, "/", month, "/", year, " ", hours, ":", minutes, ":", seconds, " "])
        
        return date
    
    #splits a tweet in two, with the first part not more than 140 character.
    #Then appends the @reply and timestamp to the rest and queues the post
    def _tweet_split(self, post):
        
        user = post[post.index('@'):post.index(' ',post.index('@'))] 
        
        #find the index of a space less than 140 character in
        #and split the string around it
        for count, symbol in enumerate(post[:141][::-1]):
            if symbol == " ":
                good_post = post[:141-count]
                post = self._timestamp() + user + post[140-count:]
                self.post_queue.appendleft(post)
                break
            
        return good_post
                