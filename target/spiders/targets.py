import re
import json
import scrapy
import requests
from scrapy.cmdline import execute

class TargetsSpider(scrapy.Spider):
    name = 'targets'
    allowed_domains = ['target.com']

    start_urls = ["https://www.target.com"]

    def start_requests(self):
        urls = ["https://www.target.com/p/-/A-79344798",'https://www.target.com/p/-/A-13493042','https://www.target.com/p/-/A-85781566']
        headers = {
            'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            'accept-encoding': "gzip, deflate, br",
            'accept-language': "en-GB,en;q=0.9",
            'cache-control': "no-cache",
            'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
        }
        for url in urls:
            yield scrapy.Request(url=url,headers=headers, callback=self.parse)


    def parse(self, response):

        main_dict = {}

        data_json = re.findall(r"'__TGT_DATA__': (.*?)\)\)", response.text)[0].strip("']").strip('"').split('JSON.parse("')[-1]
        jdata = data_json.replace('''\\\\\\"''', '').replace('\\"', '"')
        data1 = json.loads(jdata)

        url = response.url

        try:
            json_data = data1['__PRELOADED_QUERIES__']['queries'][2][1]['product']
        except Exception as e:
            print(e)

        item = {}

        item['url'] = response.xpath('//*[@property="og:url"]/@content').get()
        item['tcin'] = json_data['tcin']

        try:
            item['upc'] = json_data['item']['primary_barcode']
        except:
            item['upc'] = ""

        # ==========================Code for price ================================
        try:
            # price = json_data['price']['current_retail_min']
            price = json_data['price']['formatted_current_price']
            if "-" in price:
                price = price.split("-")[0]
            regex = re.compile(r"[^\d\-+\.]")
            item['price_amount'] = float(regex.sub("", price))
        except Exception as e:
            print(e, "Please check price ", url)
        # ==========================================================================

        item['currency'] = "USD"
        item['description'] = response.xpath('//*[@property="og:description"]/@content').get()
        item['specs'] = []
        item['ingredients'] = ""
        item['bullets'] = "\\n".join(json_data['item']['product_description']['soft_bullets']['bullets'])

        # ============================ Code for features ========================================
        features_path = json_data['item']['product_description']['bullet_descriptions']
        html_tag_regex = re.compile("<.*?>")
        cleaned_strings = []
        for string in features_path:
            cleaned_strings.append(html_tag_regex.sub("", string))

        item['features'] = {key.strip(): value.strip() for key, value in
                            [string.split(":") for string in cleaned_strings]}

        # =========================================================================================

        main_dict.update(item)

        # ================================Code for scrape the questions and answers ==============================
        api_key = re.findall(r'"apiKey\\":\\"(.*?)\\"', response.text, re.DOTALL)[1]
        question_url = f"https://r2d2.target.com/ggc/Q&A/v1/question-answer?key={api_key}&page=0&questionedId={item['tcin']}&type=product&size=10&sortBy=MOST_ANSWERS&errorTag=drax_domain_questions_api_error"
        request = requests.request("GET", question_url)

        datas = json.loads(request.text)['results']

        questions = []  # =======Main list where store all questions and answers =======

        for data in datas:
            q_a_dict = {}
            q_a_dict['question_id'] = data['id']
            q_a_dict['submission_date'] = data['submitted_at']
            q_a_dict['question_summary'] = data['text']

            try:
                q_a_dict['user_nickname'] = data['author']['nickname']
            except:
                q_a_dict['user_nickname'] = ""

            q_a_dict['answers'] = []

            ans = data['answers']
            for an in ans:
                answer_dict = {}
                answer_dict['answer_id'] = an['id']
                answer_dict['answer_summary'] = an['text']
                answer_dict['submission_date'] = an['submitted_at']
                answer_dict['user_nickname'] = an['author']['nickname']
                q_a_dict['answers'].append(answer_dict)

            questions.append(q_a_dict)

        final_q_a_dict = {"questions": questions}
        main_dict.update(final_q_a_dict)

        print(json.dumps(main_dict))

execute("scrapy crawl targets ".split())
