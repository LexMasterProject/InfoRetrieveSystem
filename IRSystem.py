"""\
------------------------------------------------------------
USE: python <PROGNAME> (options) file1...fileN
OPTIONS:
    -h : print this help message
    -s FILE : use stoplist file FILE
------------------------------------------------------------
"""

import sys, re, getopt,Collection,math,pickle,PorterStemmer

class CommandLine:
    def __init__(self):
        opts, args = getopt.getopt(sys.argv[1:],'q:s:c:i:h:S:L:r:Q:N:a:o:')
        opts = dict(opts)
        self.argfiles = args
        self.stops = set()
        self.query=list()
        self.collectionName=''
        self.indexfile=''
        self.loadfile=''
        self.queryfile=''
        
        self.createIndex=False
        self.storeIndex=False
        self.loadIndex=False
        self.boolRetrieval=False
        self.rankedRetrieval=False
        self.rankedRetrievalid=0
        self.rankedRetrievalAll=False

        if '-h' in opts:
            self.printHelp()
        
        if '-s' in opts:
            self.readStopList(opts['-s'])

        if '-c' in opts:
            self.collectionName=opts['-c']
            self.createIndex=True
            
        if '-q' in opts:
            self.readQuery(opts['-q'])
            self.boolRetrieval=True
            
        if '-S' in opts:
            self.indexfile=opts['-S']
            self.storeIndex=True
            
        if '-L' in opts:
            self.loadfile=opts['-L']
            self.loadIndex=True
            
        if '-r' in opts:
            self.rankedRetrieval=True
            self.readQuery(opts['-r'])
            
        if '-Q' in opts:
            self.rankedRetrievalid=opts['-Q'] 
            collection=Collection.Collection(opts['-Q'])
            for doc in collection.docs():
                if doc.docid==int(opts['-N']):
                    self.query=doc.lines
                    
        if '-a' in opts:
            self.rankedRetrievalAll=True
            self.queryfile=opts["-a"]

    def printHelp(self):
        helpdoc = __doc__.replace('<PROGNAME>',sys.argv[0],1)
        print >> sys.stderr, helpdoc
        exit()

    def readStopList(self,stop_file):
        f = open(stop_file,'r')
        for line in f:
            self.stops.add(line.strip())
            
    def readQuery(self,query):
        self.query.append(query)
        
    
            
            
class IRSystem:
    def __init__(self,config):
        self.termDocCount={}
        self.docTermCount={}
        self.termCounts={}
        self.config=config
        self.tokenRe=re.compile("[a-z0-9]+")
        self.stops=config.stops
        self.query=config.query
        self.boolRetrSet=set()
        self.totalDoc=0
        self.docSize={}
        self.indexfile=config.indexfile
        self.loadfile=config.loadfile
        self.docScores={}
        self.porterStemmer=PorterStemmer.PorterStemmer()
       
    def addTermCount(self,term,v):
        if term in self.termCounts:
            self.termCounts[term]+=v
        else:
            self.termCounts[term]=v
            
    def addTermDocCount(self,term,doc,v):
        if term not in self.termDocCount:
            self.termDocCount[term]={}
        if doc in self.termDocCount[term]:
            self.termDocCount[term][doc]+=v
        else:
            self.termDocCount[term][doc]=v
            
    def addDocTermCount(self,docid,term,v):
        if docid not in self.docTermCount:
            self.docTermCount[docid]={}
        if term in self.docTermCount[docid]:
            self.docTermCount[docid][term]+=v
        else:
            self.docTermCount[docid][term]=v 
        
    def index(self):
        collectionName=self.config.collectionName
        collection=Collection.Collection(collectionName)
        for doc in collection.docs():
            #the collection |D|
            self.totalDoc+=1
            for line in doc.lines:
                for token in self.tokenize(line):
                    if token not in self.stops:
                        self.addTermCount(token, 1)    
            for k,v in self.termCounts.iteritems():
                #get the index
                self.addTermDocCount(k, doc.docid, v)
                #get docsize----|d|
                self.getDocSize(doc.docid, self.termCounts)
                #get doc term count---tf in doc
                self.addDocTermCount(doc.docid, k, v)
            self.termCounts={}
    
    def rankedRetrieval(self):
        #index the query
        self.termCounts={}
        for line in self.query:
            for token in self.tokenize(line):
                if token not in self.stops:
                    self.addTermCount(token, 1)
        
    def cosQandDoc(self):
        for docid in self.docTermCount.iterkeys():
            similiarity=0
            for word,count in self.termCounts.iteritems():
                
                if word in self.docTermCount[docid]:
                    idf=self.getInverseDocFre(word)
                    qi=count*idf
                    di=self.docTermCount[docid][word]*idf
                else:
                    di=0
                    qi=0
                similiarity+=qi*di
            similiarity/=self.docSize[docid]
            self.docScores[docid]=similiarity
    
    def listRank(self):            
        ranks=sorted(self.docScores.iteritems(),key=lambda x:x[1],reverse=True)
        return ranks
        
            
    
    def boolRetrieval(self):
        for word in self.query:
            if self.boolRetrSet:
                self.boolRetrSet= self.boolRetrSet & set(self.termDocCount[word].keys())
            else:
                self.boolRetrSet=set(self.termDocCount[word].keys())
        
        
        
    #tokenize a line 
    #yield interator    
    def tokenize(self,line,useStem=True):
        mm=self.tokenRe.finditer(line.lower())
        if mm:
            for m in mm:
                word=m.group()
                if useStem:
                    yield self.porterStemmer.stem(word, 0, len(word)-1)
                else:
                    yield word
                
    #calc the dfw    
    def getDocFreq(self,word):
        return len(self.termDocCount[word])
        
    #calc the idf
    def getInverseDocFre(self,word):
        return math.log10(self.totalDoc/self.getDocFreq(word))
       
    
    #calc the doc size
    def getDocSize(self,docid,termCounts):
        sum_squres=sum(value*value for value in termCounts.itervalues())
        self.docSize[docid]=math.sqrt(sum_squres)
             
    def storeIndex(self):
        with open(self.indexfile,'wb') as savedata:
            pickle.dump(self.termDocCount,savedata)
            
    def loadIndex(self):
        with open(self.loadfile,'rb') as restoredata:
            self.termDocCount=pickle.load(restoredata)
            docidSet=set()
            for word,docCount in self.termDocCount.iteritems():
                for docid,termCount in docCount.iteritems():
                    docidSet.add(docid)
                    #get doc term count---tf in doc
                    self.addDocTermCount(docid, word, termCount)
            #the collection |D|  
            self.totalDoc=len(docidSet) 
            #get doc size----|d|
            for docid,termCount in self.docTermCount.iteritems():
                self.getDocSize(docid, termCount) 
                 
             
if __name__ == '__main__':
    config=CommandLine()
    docsSystem=IRSystem(config)
    if config.createIndex:
        print '*'*20,'create index','*'*20
        docsSystem.index()
        print '...Done'
    if config.storeIndex:
        print '*'*20,'store index','*'*20
        docsSystem.storeIndex()
        print '...Done'
    if config.loadIndex:
        print '*'*20,'load index','*'*20
        docsSystem.loadIndex()
        print '...Done'
    if config.boolRetrieval:
        print '*'*20,'boolean retrieval','*'*20
        docsSystem.boolRetrieval()
        for docid in docsSystem.boolRetrSet:
            print docid
        print '...Done'
    if config.rankedRetrieval:
        print '*'*20,'ranked retrieval','*'*20
        docsSystem.rankedRetrieval()
        docsSystem.cosQandDoc()
        ranks=docsSystem.listRank()
        n=min(len(ranks),10)
        for rank in ranks[:n]:
            print rank[0],' ',rank[1]
        print '...Done'
    if config.rankedRetrievalid:
        print '*'*20,'ranked retrieval from queryset','*'*20
        docsSystem.rankedRetrieval()
        docsSystem.cosQandDoc()
        ranks=docsSystem.listRank()
        n=min(len(ranks),10)
        for rank in ranks[:n]:
            print rank[0],"  ",rank[1]
        print '...Done'
    if config.rankedRetrievalAll:
        print '*'*20,'ranked retrieval from queryfiles','*'*20
        collection=Collection.Collection(config.queryfile)
        with open("example.txt","w") as outfs:
            for doc in collection.docs():
                docsSystem.query=doc.lines
                docsSystem.rankedRetrieval()
                docsSystem.cosQandDoc()
                ranks=docsSystem.listRank()
                n=min(len(ranks),10)
                for rank in ranks[:n]:
                    form="%d %d\n"%(doc.docid,rank[0])
                    outfs.write(form)
        print '...Done'
        
        
        
    
        
        
    

   

    
    

    
    
   
    
   
    
   
        
    
   

   

   

 

        
    
    
       
    
    
  
    
   
   
            
