import streamlit as st
import requests
import asyncio
import aiohttp
import time
import argparse

from pathlib import Path

orig_url = "https://www.thegradcafe.com/survey/?per_page=40"

parser = argparse.ArgumentParser()
parser.add_argument("pages",help="Number of pages to scrape",type=int,default=10)
parser.add_argument("url_form",help="The URL template",default=orig_url)

#parser.add_argument("-q", "--query", default="",help="Catch-all query")
#parser.add_argument("-i", "--institution", default="",help="Institution name")
#parser.add_argument("-p", "--program", default="",help="Program name")
#parser.add_argument("-d", "--degree", default="",help="Degree type")

parser.add_argument("-f", "--filename",default="file",help="Output file name")

args = parser.parse_args()

#url_form = "".join(["https://www.thegradcafe.com/survey/?per_page=40","&q=",args.query,"&institution=",args.institution,
#                  "&program=",args.program,"&degree=",args.degree,"&page="])

url_form = args.url_form

params = {}
DATA_DIR = './data/'

async def scrape(sess, url, params, page):
    async with sess.get(url=url, params=params) as response:
        contents = None
        try:
            contents = await response.text()
        except Exception as e:
            print("Unable to decode using utf8")

        if contents is None:
            contents = ''
            try:
                contents = await response.text('latin-1')
            except Exception as e:
                print("Unable to decode using latin-1")

#         if contents is None:
#             contents = ''

    fname = "{data_dir}{query}/{page}.html".format(
        query=args.filename,
        data_dir=DATA_DIR,
        page=str(page)
    )

    with open(fname, 'w') as f:
        f.write(contents)
    print("getting {0}...".format(page))

async def bound_fetch(semaphore, sess, url, params, page):
    async with semaphore:
        await scrape(sess, url, params, page)

async def main(urls: dict):
    Path("{data_dir}{query}".format(data_dir=DATA_DIR, query=args.filename)).mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(5)
    async with aiohttp.ClientSession() as sess:
        await asyncio.gather(*[bound_fetch(semaphore, sess, url, params, page) for page, url in urls.items()])

if __name__ == '__main__':
    urls = {}
    for i in range(1, args.pages+1):
        urls[i] = url_form + str(i)

    start = time.time()
    asyncio.run(main(urls))
    end = time.time()
    print("It took {} seconds to scrape gradcafe.".format(end-start))
