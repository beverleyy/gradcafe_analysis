from bs4 import BeautifulSoup
import datetime, time
import re
import argparse
import os.path
import pandas

#python3 parse.py [path_to_directory_with_html_files] [title_of_csv] [number_pages]

parser = argparse.ArgumentParser()
parser.add_argument("filename",help="Title of CSV",default="file")
parser.add_argument("path",help="Path to directory with HTML files",default="./data")
parser.add_argument("pages",help="Number of pages to scrape",type=int,default=10)

args = parser.parse_args()

CSEM = [
    'Computational Engineering And Sciences (CSEM)',
    'Computational Science Engineering And Mathematics (CSEM)',
    'Computational Science, Engineering And Mathematics (CSEM)',
    'Computational Science, Engineering, And Mathematics (CSEM)',
    'Computation Science, Engineering And Mathematics (CSEM)',
    'Computational Engineering And Sciences',
    'Computational Science Engineering And Mathematics',
    'Computational Science, Engineering And Mathematics',
    'Computational Science, Engineering, And Mathematics',
    'Computational Science And Engineering Mathematics',
    'Computation Science, Engineering And Mathematics',
    'Csem'
]

REPS = [
    ('Mechcanical','Mechanical'),
    ('Mechancial','Mechanical')
]


# PROGS = [
#     ('Aerospace Engineering','Aerospace Engineering'),
#     ('Mechanical And Aerospace Engineering','Mechanical Engineering'),
#     ('Mechcanical And Aerospace Engineering','Mechanical Engineering'),
#     ('Mechanical Engineering','Mechanical Engineering'),
#     ('Mechancial Engineering','Mechanical Engineering'),
#     ('Mechanical','Mechanical Engineering'),
#     ('Aerospace','Aerospace Engineering'),
#     ('Aeronautics','Aerospace Engineering'),
#     ('Aeronautical','Aerospace Engineering'),
#     ('Aeronautics & Astronautics','Aerospace Engineering'),
#     ('Aerospace Engineering Sciences','Aerospace Engineering'),
#     ('Aerospace And Mechanical Engineering','Mechanical Engineering'),
#     ('CSEM','Computational Sciences, Engineering And Mathematics (CSEM)')
# ]

DEGREE = [
    ('MFA', 'MFA'),
    ('M Eng', 'MEng'),
    ('MEng', 'MEng'),
    ('M.Eng', 'MEng'),
    ('Masters', 'MS'),
    ('PhD', 'PhD'),
    ('MBA', 'MBA'),
    ('Other', 'Other'),
    ('EdD', 'Other'),
    ('PsyD','Other'),
    ('IND','Other'),
    ('JD','Other')
]

COLLEGES = [
    ('Stanford University','Stanford University'),
    ('Stanford', 'Stanford University'),
    ('University of Michigan (Ann Arbor)','University of Michigan (Ann Arbor)'),
    ('University of Michigan','University of Michigan (Ann Arbor)'),
    ('Michigan', 'University of Michigan (Ann Arbor)'),
    ('University of Colorado, Boulder', 'University of Colorado, Boulder'),
    ('University of Colorado Boulder', 'University of Colorado, Boulder'),
    ('CU Boulder', 'University of Colorado, Boulder'),
    ('Princeton University', 'Princeton University'),
    ('Princeton', 'Princeton University'),
    ('California Institute of Technology','California Institute of Technology'),
    ('Caltech','California Institute of Technology'),
    ('University of Texas at Austin','University Of Texas At Austin'),
    ('University of Texas-Austin','University Of Texas At Austin'),
    ('The University of Texas - Austin','University Of Texas At Austin'),
    ('UT Austin','University Of Texas At Austin')
]

STATUS = ['American','International','Other']
DECISIONS = ["Accepted","Rejected","Wait listed","Interview","Other"]

MODES = [
    ("E-mail","Email"),
    ("Email","Email"),
    ("Phone","Phone"),
    ("Website","Website"),
    ("Web site","Website"),
    ("Postal service","Post"),
    ("Post","Post"),
    ("Other","Other"),
    ("Unknown","Other")
]

def proc(index,col):
    
    inst,major,season,status,date_add,date_add_ts,comment = None,None,None,None,None,None,None
    decisionfin,method,decdate,decdate_ts=None,None,None,None
    gre_q,gre_v,gre_awa,gpa,degree = None,None,None,None,None

    if len(col) != 7:
        return
    
    ## inst and major
    try:
        txtData = col.contents[1].findAll(text=True)[0]
        for k in CSEM:
            txtData = txtData.replace(k,'CSEM')
        for k,v in REPS:
            txtData = txtData.replace(k,v)
        (major,inst) = txtData.split(",",1)[0:2]
        major = major.strip().replace("CSEM",'Computational Sciences, Engineering And Mathematics (CSEM)')
        for i,name in COLLEGES:
            if i.lower() in inst.lower():
                inst = name
                break
        inst = inst.strip()
    except:
        print("Couldn't retrieve institution and major")
        
    ## comment
    try:
        comment = col.contents[1].findAll('span',class_='text-secondary')[0].get_text(strip=True)
    except:
        print("Couldn't retrieve comment")
        
    ## date added
    try:
        date_addtxt = col.contents[3].text.strip().replace("Added on ","")
        date_add_date = datetime.datetime.strptime(date_addtxt,"%B %d, %Y")
        date_add_ts = date_add_date.strftime('%s')
        date_add = date_add_date.strftime('%d-%m-%Y')
    except:
        print("Couldn't retrieve date_add")
        
    ## ['acc_date','season','student_status','gre_q','gre_v','gre_awa','gpa','degree']
    try:
        infos = []
        spans = col.contents[5].findAll('span',class_='badge')
        for span in spans[:-1]:
            t = span.get_text(strip=True)
            t = " ".join(t.split())
            infos.append(t)
        
        ## info 1 should be season
        ## except for pre-fall 2018... dammit gradcafe
        ist=1
        try:
            season = infos[1]
            year = infos[1].split(" ")[1]
            ist+=1 #change index start to 2
        except:
            year = date_add_date.date().year
            season = " ".join(["Fall",str(year)])
        
        ## info 0 should be decision + date
        decision = infos[0]
        try:
            for pds in DECISIONS:
                if pds.lower() in decision.lower():
                    decisionfin = pds
                    break
                else:
                    decisionfin = "Other"        
            for (mstr,meth) in MODES:
                if mstr.lower() in decision.lower():
                    method = meth;
                    break
            if "on" in decision.lower():
                decdate = decision.split("on")[1].strip()
                decdate_date = datetime.datetime.strptime(" ".join([decdate,str(year)]), '%d %b %Y')
                decdate_ts = decdate_date.strftime('%s') 
                decdate = decdate_date.strftime('%d-%m-%Y')
        except Exception as e:
            print("Couldn't assign method of reporting")
        
        ## info 2 onwards is variable
        ## ['student_status','gre_q','gre_v','gre_awa','gpa','degree']
        for info in infos[ist:]:
            
            ## First check if nationality given
            for k in STATUS:
                if k in info:
                    status = k
                    break
                        
            ## Now check GRE
            if "GRE" in info:
                if "V" in info:
                    gre_v = int(info.split("V")[1])
                elif "AW" in info:
                    gre_awa = float(info.split("AW")[1])
                else:
                    gre_q = int(info.split()[1])
                        
            # Check GPA
            elif "GPA" in info:
                gpa = float(info.split()[1])
                    
            # Check degree type
            else:
                for (k,v) in DEGREE:
                    if k in info:
                        degree = v
                        break
        
    except Exception as e:
        pass
    
    res = [inst,major,degree,season,decisionfin,method,
           decdate,decdate_ts,gpa,gre_v,gre_q,gre_awa,status,
           date_add,date_add_ts,comment]
    return res


if __name__ == '__main__':

    path = args.path
    title = args.filename
    n_pages = args.pages
    
    data = []
    for page in range(1, n_pages):
        if not os.path.isfile('{0}/{1}.html'.format(path, page)):
            print("Page {0} not found.".format(page))
            continue
            
        with open('{0}/{1}.html'.format(path,page),'r') as f:
            soup = BeautifulSoup(f.read(),features="html.parser")
        tables = soup.findAll('div',id='results-container')
        for tab in tables:
            rows = tab.findAll('div',class_='row')
            for row in rows:
                cols = row.findAll('div',class_='col')
                for col in cols:
                    pro = proc(page,col)
                    if pro is not None:
                        data.append(pro)
                        
        if page % 10 == 0:
          print("Processed 10 more pages (page {0})".format(page))

    df = pandas.DataFrame(data)
    df.columns = ["institution","major","degree","season","decisionfin","method",
                  "decdate","decdate_ts","gpa","grev","greq","greaw","status",
                  "date_add","date_add_ts","comment"]

    df.to_csv("data/{0}.csv".format(title))
