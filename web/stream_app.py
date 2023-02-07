import streamlit as st
import subprocess
import shutil
import sys
import os
import re
import numpy as np
import pandas as pd
pd.options.mode.chained_assignment = None

import seaborn as sns

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.lines as mlines
import matplotlib.patches as mpatches

import datetime

from typing import Union
from wordcloud import WordCloud, STOPWORDS

#sns.set_theme(style="white",font_scale=2)
sns.set_theme(style="dark",font_scale=2)

plt.style.use("dark_background")

###################
## DATA ANALYSIS ##
###################

def grab_data():
	file_list = os.listdir(os.path.abspath('./data'))
	csv_files = [k for k in file_list if '.csv' in k]
	df = pd.concat([pd.read_csv("".join(['./data/',f]),index_col=0) for f in csv_files],ignore_index=True)
	df['decdate'].fillna(df['date_add'], inplace=True)
	df['decdate_ts'].fillna(df['date_add_ts'], inplace=True)
	df['decdate_ts'] = df['decdate_ts'].astype('int')
	
	# Drop unused columns
	df = df.drop(columns=['method','grev','greq','greaw'])
	df['comment'] = df['comment'].fillna('')

	return df

def vec_dt_replace(series, year=None, month=None, day=None):
	return pd.to_datetime(
		{'year': series.dt.year if year is None else year,
		 'month': series.dt.month if month is None else month,
		 'day': series.dt.day if day is None else day})


def create_filter(df,
                  degree: str = None,
                  decisionfin: Union[str, list] = None,
                  institution: Union[str, list] = None,
                  prog: Union[str,list] = None,
                  gpa: bool = False):
    filt = [True] * len(df)
    if degree is not None:
        filt = (filt) & (df['degree'] == degree)
    if prog is not None:
        if isinstance(prog, str):
            filt = (filt) & (df['major'].str.contains(prog, case=False))
        elif isinstance(prog, list):
            filt = (filt) & (df['major'].str.lower().isin([x.lower() for x in prog]))
    if decisionfin is not None:
        if isinstance(decisionfin, str):
            filt = (filt) & (df['decisionfin'].str.contains(decisionfin, case=False))
        elif isinstance(decisionfin, list):
            filt = (filt) & (df['decisionfin'].str.lower().isin([x.lower() for x in decisionfin]))
    if institution is not None:
        if isinstance(institution, str):
            filt = (filt) & (df['institution'].str.contains(institution, case=False))
        elif isinstance(institution, list):
            filt = (filt) & (df['institution'].str.lower().isin([x.lower() for x in institution]))
    if gpa:
        filt = (filt) & (~df['gpa'].isna()) & (df['gpa'] <= 4)
    
    return filt

def get_uni_stats(u_df, 
                  histype: str = None, 
                  search: str = None, 
                  major: str = None,
                  title: str = None, 
                  degree: str = '', 
                  field: str = '', 
                  hue='decisionfin'
                 ):
    title = title if title is not None else search
    if degree not in ['MS', 'PhD', 'MEng', 'MFA', 'MBA', 'Other']:
        degree = None
        
    # Clean up the data a bit, this probably needs a lot more work
    # Maybe its own method, too
    u_df = u_df.copy()
    u_df = u_df[~u_df['decdate'].isna()]
    
    u_df.loc[:,'year'] = pd.to_numeric(u_df['decdate'].str[-4:],errors='coerce')
    u_df = u_df.dropna(subset=['year'])
        
    u_df = u_df[(u_df['year'] > 2000) & (u_df['year'] < datetime.datetime.now().year)]
    
    # Normalize to 2020. 2020 is a good choice because it's recent AND it's a leap year
    u_df.loc[:, 'uniform_dates'] = vec_dt_replace(pd.to_datetime(u_df['decdate'],dayfirst=True), year=2020)
    
    # Get december dates to be from "2019" so Fall decisions that came in Dec come before the Jan ones.
    dec_filter = u_df['uniform_dates'] > datetime.datetime.strptime('2020-11-30', '%Y-%m-%d')
    u_df.loc[dec_filter, 'uniform_dates'] = vec_dt_replace(pd.to_datetime(u_df[dec_filter]['uniform_dates']), year=2019)
    
    # Trying to pick red/green colorblind-friendly colors
    flatui = ["#00A36C", "#C21E56", "#FFC300"]
    sns.set_palette(flatui)
    acc_patch = mpatches.Patch(color='#00A36C80')
    rej_patch = mpatches.Patch(color='#C21E5680')
    int_patch = mpatches.Patch(color='#FFC30080')
    acc_line = mlines.Line2D([], [], color='#00A36C')
    rej_line = mlines.Line2D([], [], color='#C21E56')
    int_line = mlines.Line2D([], [], color='#FFC300')
    
    status_type = ['Accepted', 'Rejected', 'Interview']

    hue_order = status_type
    
    if hue == 'status':
        hue_order = ['American', 'International', 'Other']
        status_type = ['Accepted', 'Interview']
    
    # No more GRE, so we do 2x1
    fig,ax = plt.subplots(1,2)
    fig.set_size_inches(20,10)
    fig.patch.set_alpha(0)
    
    # Timeline stats
    mscs_filt = create_filter(u_df, degree, status_type, institution = search, prog = major)
    mscs_filt = (mscs_filt) & (u_df['uniform_dates'].astype(str) <= '2020-06-00')
    
    if histype == 'ecdf':
        stat = "count"
        sns.ecdfplot(data=u_df[mscs_filt],
                     x='uniform_dates',
                     stat=stat,
                     hue=hue,
                     hue_order=hue_order,
                     ax=ax[0]
                    )
    else:
        sns.histplot(data=u_df[mscs_filt],
                     x='uniform_dates',
                     element='step',
                     hue=hue,
                     cumulative=True,
                     discrete=False,
                     fill=False,
                     hue_order=hue_order,
                     ax=ax[0]
                    )

    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    formatter = mdates.ConciseDateFormatter(locator)
    formatter.formats = ['%b',  # years
                         '%b',       # months
                         '%d',       # days
                         '%H:%M',    # hrs
                         '%H:%M',    # min
                         '%S.%f', ]  # secs
    # Hide the year
    formatter.zero_formats = ['%b',  # years
                         '%b',       # months
                         '%d',       # days
                         '%H:%M',    # hrs
                         '%H:%M',    # min
                         '%S.%f', ]  # secs
    # Hide the year
    formatter.offset_formats = ['',  # years
                         '',       # months
                         '%d',       # days
                         '%H:%M',    # hrs
                         '%H:%M',    # mins
                         '%S.%f', ]  # secs
    
    ax[0].xaxis.set_major_locator(locator)
    ax[0].xaxis.set_major_formatter(formatter)
    h, l = ax[0].get_legend_handles_labels()
    
    # Add frequency counts
    if h is not None and l is not None:
        if hue == 'decisionfin':
            counts = u_df[mscs_filt][hue].value_counts().reindex(hue_order)
            l = [f'{value} (n={count})' for value, count in counts.items()]
            ax[0].legend(handles=[acc_line, rej_line, int_line], labels=l, title="Decision")

    ax[0].set_xlabel("Date")
    ax[0].set_ylabel("Count")
    ax[0].set_title("Cumsum of decisions")
    
    # Get GPA stats
    mscs_filt = create_filter(u_df, degree, status_type, institution = search, prog = major, gpa = True)
    
    sns.histplot(data=u_df[mscs_filt],
                 multiple="stack",
                 x='gpa',
                 hue=hue,
                 hue_order=hue_order,
                 bins=20,
                 ax=ax[1]
                )
    ax[1].set_xlabel("GPA")
    ax[1].set_ylabel("Count")
    ax[1].set_title("GPA Distribution")

    ax[1].set_xlim(2, 4)
    
    # Add frequency counts
    #h, l = ax[0][1].get_legend_handles_labels()
    h, l = ax[1].get_legend_handles_labels()
    if h is not None and l is not None:
        if hue == 'decisionfin':
            counts = u_df[mscs_filt][hue].value_counts().reindex(hue_order)
            l = [f'{value} (n={count})' for value, count in counts.items()]
            ax[1].legend(handles=[acc_patch, rej_patch, int_patch], labels=l, title="Decision")
    
    # Save file to output directory
    # fig.suptitle(title + ', ' + field + ' ', size='xx-large')
    return fig

def what_day(df_1720,
             search: str = None, 
             major: str = None,
             degree: str = '', 
            ):
	if degree not in ['MS', 'PhD', 'MEng', 'MFA', 'MBA', 'Other']:
		degree = None

	flatui = ["#00A36C80", "#C21E5680", "#FFC30080"]
	sns.set_palette(flatui)
    
	hue_order = ['Accepted', 'Rejected', 'Interview']   
	day_order = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

	df_1720['day'] = pd.to_datetime(df_1720['decdate_ts'], unit='s').dt.day_name().str[0:3]
	df_filt = create_filter(df_1720, degree, hue_order, institution=search, prog=major)

	pf = plt.figure(figsize=(5,5))
	pf.patch.set_alpha(0)

	g = sns.countplot(data=df_1720[df_filt],
	                  x='day',
	                  hue='decisionfin',
	                  hue_order=hue_order,
	                  order=day_order,
	                  saturation=1,
	                  alpha=0.7
	                 )

	g.set_xlabel("Day of week")
	g.set_ylabel("Count")
	g.set_title("Decisions per day")
    
	for item in ([g.title, g.xaxis.label, g.yaxis.label] +
	             g.get_xticklabels() + g.get_yticklabels()):
	    item.set_fontsize(14)
	g.legend(fontsize=14);

	return pf

def wordcloud(df,
              search: str = '', 
              major: str = '',
              degree: str = '',
             ):
	def plot_cloud(wordcloud):
	    pf = plt.figure(figsize=(20, 20))
	    pf.patch.set_alpha(0)
	    plt.imshow(wordcloud) 
	    plt.axis("off");
	    return pf

	# if you want for a specific school/program then filter the df accordingly
	cdf = df.loc[(df['institution'].astype(str).str.contains(search))&(df['major'].astype(str).str.contains(major))&(df['degree'].astype(str).str.contains(degree))]

	# concat all the comments into a text chunk and clean it up
	text = cdf.dropna(subset=['comment'])['comment'].str.cat(sep=' ')
	text = re.sub(r'==.*?==+', '', text)
	text = text.replace('\n', '')

	# add some stopwords
	STOPWORDS.update(['got','though','program'])
    
	# print the wordcloud
	wordcloud = WordCloud(width=540,
	                      height=540,
	                      mode="RGBA",
	                      background_color=None,
	                      colormap="summer",
	                      max_font_size=270,
	                      random_state=1,
	                      collocations=True,
	                      stopwords=STOPWORDS
	                     ).generate(text)
	return plot_cloud(wordcloud)

def interview_analysis(df_1720):
	df_1720['is_int'] = 0
	df_1720['is_acc'] = 0
	df_1720.loc[df_1720['decisionfin'] == 'Interview', 'is_int'] = 1
	df_1720.loc[df_1720['decisionfin'] == 'Accepted', 'is_acc'] = 1

	#df_1720.groupby(by='institution').agg({'is_int': sum}).sort_values(by='is_int', ascending=False).head(10)

	# Mild cleanup of institution names
	df_1720['short_inst'] = df_1720['institution'].str.split('(').str[0].str.replace('[^a-zA-Z]','',regex=True)
	df_1720['short_inst'] = df_1720['short_inst'].str.strip().str.lower()

	# Make table of interview/acceptance
	dfr = pd.DataFrame()
	dfr['Institution'] = df_1720.groupby(by='short_inst')['institution'].agg(pd.Series.mode)
	dfr['Interviews'] = df_1720.groupby(by='short_inst').agg({'is_int':sum})
	dfr['Acceptances'] = df_1720.groupby(by='short_inst').agg({'is_acc':sum})

	# Ratio of interview to acceptance
	dfr = dfr.loc[~((dfr['Acceptances'] == 0))]
	dfr['Ratio'] = dfr['Interviews']/dfr['Acceptances']

	return dfr.sort_values(by='Interviews', ascending=False).head(16).reset_index(drop=True)


def default_view(df_1720,if_recent):
	iview = interview_analysis(df_1720)

	fig1 = get_uni_stats(df_1720,histype='ecdf',title='All Universities')
	fig2 = what_day(df_1720)
	with st.container():
		st.markdown("# Entire dataset")
		if if_recent:
			st.markdown("## Last 5 years only")

		st.write(fig1)
		col1,col2 = st.columns(2)
		col1.markdown("### Interview ratio")
		col1.dataframe(iview,use_container_width=True)
		col2.markdown("### Day of week")
		col2.write(fig2)


############
## OUTPUT ##
############

@st.cache(suppress_st_warning=True,max_entries=1)
def view_dash(show_all,show_recent,as_table):
	with st.empty():
		try:
			df = grab_data()
			if show_recent:
				df_1720 = df[(df['season'].isin(['Fall 2018', 'Fall 2019', 'Fall 2020', 'Fall 2021','Fall 2022','Fall 2023']))]
			else:
				df_1720 = df

			if show_all:
				if not as_table:
					default_view(df_1720,show_recent)
				else:
					with st.container():
						st.markdown("# Entire dataset")
						if show_recent:
							st.markdown("## Last 5 years only")
						st.dataframe(df_1720,use_container_width=True)
			else:
				if not as_table:
					with st.container():
						st.markdown("".join(["# ",inst,", ",major," ",deg]))
						if show_recent:
							st.markdown("## Last 5 years only")
						fig1 = get_uni_stats(df_1720, histype='ecdf',search=inst,major=major,degree=deg)
						fig2 = what_day(df_1720, search=inst, major=major, degree=deg)
						fig3 = wordcloud(df_1720, search=inst, major=major, degree=deg)
						st.write(fig1)
						col3,col4 = st.columns(2)
						col3.write(fig2)
						col4.write(fig3)
				else:
					with st.container():
						st.markdown("".join(["# ",inst,", ",major," ",deg]))
						if show_recent:
							st.markdown("## Last 5 years only")
						filt = create_filter(df_1720, deg, institution=inst, prog=major)
						st.dataframe(df_1720[filt],use_container_width=True)
		except:
			with st.container():
				st.markdown("# No data available")
				st.write("Please use the scraper in the sidebar.")

#############
## SIDEBAR ##
#############

url_form = "https://www.thegradcafe.com/survey/?per_page=40"

with st.sidebar:
	tab1, tab2 = st.tabs(["Search Dataset", "Scrape Data"])
	with tab1:
		with st.form(key='stats'):
			inst = st.text_input('Institution:',value="")
			major = st.text_input('Major:',value="")
			deg = st.selectbox('Degree type:',["","MS","PhD"])
			gen_data = st.form_submit_button(label='Generate stats')

		show_all = st.button('Show entire dataset')
		show_recent = st.checkbox('Show last 5 years only')
		as_table = st.checkbox('View as table')

	with tab2:
		with st.form(key='scraper'):
			pages = st.number_input('Number of pages to scrape:',min_value=1,step=1,help="More pages = longer time, but more data")
			query = st.text_input('Regex query:',value="")
			institution = st.text_input('Institution:',value="")
			program = st.text_input('Program:',value="")
			degree = st.selectbox('Degree type:',["","MS","PhD"])
			submit_button = st.form_submit_button(label='Scrape')

		if st.button('Clear cached data'):
			shutil.rmtree('./data',ignore_errors=True,onerror=None)

def generate_url():
	return "".join(["https://www.thegradcafe.com/survey/?per_page=40","&q=",query,"&institution=",institution,"&program=",program,"&degree=",degree,"&page="])

@st.cache(suppress_st_warning=True,max_entries=1)
def call_scraper(url_form):
	subprocess.call([f'{sys.executable}','scraper_app.py',str(pages),url_form])
	subprocess.call([f'{sys.executable}','parser_app.py','file','data/file',str(pages)])

view_recent = 0
view_table = 0

if 'if_all' not in st.session_state:
	st.session_state['if_all'] = 1
if show_all:
	st.session_state['if_all'] = 1
if gen_data:
	st.session_state['if_all'] = 0

view_all = st.session_state['if_all']
view_recent = 1 if show_recent else 0
view_table = 1 if as_table else 0

if submit_button:
	url_form = generate_url()
	call_scraper(url_form)
	view_dash(view_all,view_recent,view_table)
else:
	view_dash(view_all,view_recent,view_table)

