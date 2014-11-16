
import re, sys

class Collection:
    def __init__(self,file):
        self.collection_file=file

    def docs(self):
        input=open(self.collection_file,'r')
        startdoc=re.compile('<document docid=(\d+)\s*>')
        enddoc=re.compile('</document\s*>')
        readingDoc=False
        for line in input:
            m=startdoc.search(line)
            if m:
                readingDoc=True
                doc=Document()
                doc.docid=int(m.group(1))
            elif enddoc.search(line):
                readingDoc=False
                yield doc
            elif readingDoc:
                doc.lines.append(line)
        input.close()

class Document:
    def __init__(self):
        self.docid=0
        self.lines=[]

    def printDoc(self,out=sys.stdout):
        print >> out, "\n[DOCID: %d]" % self.docid
        for line in self.lines:
            print >> out, line,

