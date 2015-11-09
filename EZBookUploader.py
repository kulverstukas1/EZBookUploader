# Author: Kulverstukas
# Date: 2015.04.20
# Website: Evilzone.org; http://9v.lt/blog
# Description:
#   Automatic ebook (pdf) uploader. Converts first 10 pages of the PDF
#   into text and extracts the ISBN, by which it then extracts more info
#   from worldcat.org, uploads the file to EZ and generates BBCode.

import re
import os
import mechanize
import evilupload
from evilupload import *
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from cStringIO import StringIO

#======================================================
ezup = evilupload()
ezLogin = ezup.login()
if ezLogin is not None:
    print('Logged in')
else:
    print('Login failed. Exiting...!')
    exit()
if (not os.path.exists("Uploaded")): os.mkdir("Uploaded")
if (not os.path.exists("No_ISBN")): os.mkdir("No_ISBN")
#======================================================
def convertPdf(path):
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = file(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos=set(range(1, 10))
    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password,caching=caching, check_extractable=True):
        interpreter.process_page(page)
    fp.close()
    device.close()
    str = retstr.getvalue()
    retstr.close()
    return str
#======================================================
def extractInfo(isbn):
    result = {"title":"", "summary":"", "bookimg":""}
    br = mechanize.Browser()
    br.addheaders = [('User-agent', ' Mozilla/5.0 (Windows NT 6.1; rv:30.0) Gecko/20100101 Firefox/30.0')]
    br.set_handle_robots(False)
    br.open("http://www.worldcat.org/search?qt=worldcat_org_all&q=%s" % isbn)
    try:
        resp = br.follow_link(url_regex="title*", nr=0).read() # first link
    except:
        return result
    # with open("debug.txt", "w") as a: a.write(resp)
    title = re.search("<h1 class=\"title\">.+?</h1>", resp)
    if title:
        result["title"] = title.group(0).replace("<h1 class=\"title\">", "").replace("</h1>", "")
    
    summary = re.search("<div id=\"summary\">.+?</div>", resp, re.DOTALL)
    if not summary:
        summary = re.search("<p class=\".*?review\">.+?</p>", resp, re.DOTALL)
        if summary:
            repl = re.search("<p class=\".*?review\">", summary.group(0))
            result["summary"] = summary.group(0).replace(repl.group(0), "").replace("</p>", "").strip()
    else:
        repl = re.search("<div id=\"summary\">", summary.group(0))
        result["summary"] = summary.group(0).replace(repl.group(0), "").replace("</div>", "").strip()
    repl = re.search("<span.+?showMoreLessContentElement.+?>", result["summary"])
    if repl:
        result["summary"] = result["summary"].replace(repl.group(0), "").replace("</span>", "")
        repl = re.search("<span.+?showMoreLessControlElement.+", result["summary"], re.DOTALL)
        result["summary"] = result["summary"].replace(repl.group(0), "").strip()
        
    imgUrl = re.search("<img class=\"cover\".+?/>", resp)
    if imgUrl:
        repl = re.search("src=\".+?jpg", imgUrl.group(0))
        result["bookimg"] = "http:"+repl.group(0).replace("src=\"", "")
    
    return result
#======================================================
def sanitizeFilename(filename):
    allowedSymbols = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0987654321.-_ ()[]+,~"
    newFilename = filename.split(".")[0]
    for symbol in filename:
        if (symbol not in allowedSymbols):
            newFilename = newFilename.replace(symbol, "")
    if (len(newFilename) > 47):
        newFilename = newFilename[:46].strip()
    newFilename = newFilename.replace(" ", "_")+".pdf"
    return newFilename
#======================================================
def generateBBCode(upUrl, info, filename):
    if (info["summary"] is ""): info["summary"] = "No summary :/"
    return "%s\n\n[img]%s[/img]\n\n[quote]%s[/quote]\n\nDownload: [url=%s]%s[/url]" % (info["title"], info["bookimg"], info["summary"], upUrl, filename)
#======================================================
def generateWikiCode(upUrl, title):
    return "* [%s %s]" % (upUrl, title)
#======================================================

wikiCode = ""
for filename in os.listdir("."):
    if (os.path.isfile(filename) and filename.endswith(".pdf")):
        print "Processing '%s'..." % filename
        text = convertPdf(filename)
        isbns = re.findall('(?:[0-9]{3}-)?[0-9]{1,5}-[0-9]{1,7}-[0-9]{1,6}-[0-9]', text)
        if (len(isbns) > 0):
            goodFilename = sanitizeFilename(filename)
            os.rename(filename, goodFilename)
            print "Found ISBN: %s, extracting info..." % isbns[0]
            info = extractInfo(isbns[0]) #; print info; print "\n"; exit()
            print "Uploading as '%s'...\n" % goodFilename
            upUrl = ezup.fileupload(goodFilename)
            try:
                os.rename(goodFilename, "Uploaded/"+goodFilename)
            except:
                for num in range(1000):
                    if (not os.path.exists("Uploaded/"+goodFilename[:-4]+str(num)+".pdf")):
                        os.rename(goodFilename, "Uploaded/"+goodFilename[:-4]+str(num)+".pdf")
                        break
            if (os.path.exists(goodFilename[:-4]+".txt")):
                for num in range(1000):
                    if (not os.path.exists(goodFilename[:-4]+str(num)+".txt")):
                        goodFilename = goodFilename[:-4]+str(num)+".txt"
                        break
            try:
                with open(goodFilename[:-4]+".txt", "w") as bbOut: bbOut.write(generateBBCode(upUrl, info, filename))
            except TypeError:
                with open(goodFilename[:-4]+".txt", "w") as bbOut: bbOut.write(unicode(generateBBCode(upUrl, info, filename), "utf-8"))
            if ((info["title"] is not "") and (info["bookimg"] is not "")):
                wikiCode += generateWikiCode(upUrl, info["title"])+"\n"
            else:
                wikiCode += generateWikiCode(upUrl, filename)+"\n"
        else:
            try:
                os.rename(filename, "No_ISBN/"+filename)
            except:
                for num in range(1000):
                    if (not os.path.exists("No_ISBN/"+filename[:-4]+str(num)+".pdf")):
                        os.rename(filename, "No_ISBN/"+filename[:-4]+str(num)+".pdf")
                        break
            print "Didn't find ISBN in file '%s'\n" % filename
        
        if (wikiCode is not ""):
            try:
                with open("wikiCodes.txt", "w") as wikiOut: wikiOut.write(wikiCode)
            except TypeError:
                with open("wikiCodes.txt", "w") as wikiOut: wikiOut.write(unicode(wikiCode, "utf-8"))
# print extractInfo("973-545455665455")
