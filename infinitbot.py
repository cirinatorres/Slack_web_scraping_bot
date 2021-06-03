# Author: Daniel Torres

# Monitor the website https://releases.43einhalb.com/en/ and
# send a message to Slack when a new raffle is published.
# It must use Python and the modul requests (not webdriver).

import requests

# from bs4 import BeautifulSoup
from time import sleep
from user_agent import generate_user_agent
from lxml.html import fromstring
from slack_webhook import Slack


AGENT = generate_user_agent(os=('mac', 'linux'))
HEADERS = {'User-Agent': AGENT}


# Receives an HTML element and returns its text attribute
def get_text_from_element(element):
	return element.xpath('./text()')[0]


# Receives a url and returns the requests' response
def get_url_response(url):
	global HEADERS
	response = requests.get(url, headers=HEADERS)
	return response


# Receives a requests' response and checks if the response is 200
def response_is_200(response):
	return response.status_code == requests.codes.ok


# Receives a requests' response and builds the html tree
def get_html_tree(response):
	html_tree = fromstring(response.text)
	return html_tree


# Receives the HTML tree and returns a list with all the open raffle elements
def get_list_of_open_raffles(html_tree):
	list_of_open_raffles = html_tree.xpath('//span[@class="display-variation raffle"]')
	return list_of_open_raffles


# Receives an element, a location={".","/"} to know the scope of the search,
# a tag={"span","li","p",...} to distinguish the tag field,
# an attribute={"class","id",...} to identify the attribute inside the element and
# the name=name of the attribute. Returns the first sibling of the element inside the HTML tree
def get_sibling_element(element, location, tag, attribute, name):
	parent = element.xpath('..')[0]
	sibling = parent.xpath(location + '/' + tag + \
		'[@' + attribute + \
		'="' + name + '"]')[0]
	return sibling


# Receives an element which is a sneaker and returns the specific url of the raffle.
def get_sneaker_raffle_url(sneaker_element):
	global main_url
	sneaker_url = sneaker_element.xpath("./a[contains(@href, '/en/')]")[0].get('href')
	sneaker_url = main_url[:-4] + sneaker_url
	return sneaker_url


# Receives the HTML tree of the sneaker's url and returns its picture url.
def get_picture(sneaker_tree):
	picture_url = sneaker_tree.xpath('//img[@itemprop="associatedMedia"]')[0]
	picture_url = picture_url.get('src')
	return picture_url


# Receives the HTML tree of the sneaker's url and returns its model, brand and reference code.
def get_model_brand_referenceCode(sneaker_tree):
	brand_and_model_element = sneaker_tree.xpath('//h1[@class="h3"]')[0]
	brand_and_model = get_text_from_element(brand_and_model_element)
	brand = brand_and_model.split('-')[0]
	model = brand_and_model.split('-')[1]
	sibling = get_sibling_element(brand_and_model_element, '/', 'span', 'class', 'text-muted')
	referenceCode = get_text_from_element(sibling)
	return model, brand, referenceCode


# Receives the HTML tree of the sneaker's url and returns its value and currency.
def get_price(sneaker_tree):
	price_element = sneaker_tree.xpath('//span[@class="price h3 m-0 py-1"]')[0]
	price = get_text_from_element(price_element)
	if price[0] == '€':
		currency = 'EUR'
	elif price[0] == '$':
		currency = 'USD'
	else:
		raise NameError('CurrencyNotInTheSystem')
	value = price[1:]
	return value, currency


# Receives the HTML tree of the sneaker's url and returns its raffle closing date.
def get_closing_date(sneaker_tree):
	date = sneaker_tree.xpath('//li[contains(text(), "Raffle closes on")]')[0]
	date = get_text_from_element(date)
	month = date.split(',')[0].split()[3]
	day = date.split(',')[0].split()[4][:-2]
	hour = date.split(',')[1].split()[2]
	time_zone = date.split(',')[1].split()[4][:-1]
	return month, day, hour, time_zone


# Receives the HTML tree of the sneaker's url and returns its minimum, maximum and country size.
def get_sizes(sneaker_tree):
	parent = sneaker_tree.xpath('//select[@id="selectVariation"]')[0]
	min_size = parent.xpath('./option[@class="text-muted dropdown-item"]')[0]
	min_size = get_text_from_element(min_size)
	country = min_size.split('·')[1].split()[1][:-1]
	min_size = min_size.split('·')[1].split()[0]
	max_size = parent.xpath('./option[@class="text-muted dropdown-item"]')[-1]
	max_size = get_text_from_element(max_size)
	max_size = max_size.split('·')[1].split()[0]
	return min_size, max_size, country


# Receives the Slack channel url, the sneaker's raffle url, picture url, model, brand, reference code,
# value, currency, month, day, hour and timezone in which the raffle closes,
# minimum, maximum and country size.
# Proceeds to send a Webhook message to the Slack channel.
# Reference to build the message - https://app.slack.com/block-kit-builder/T023DP1C5PH#%7B%22blocks%22:%5B%5D%7D
def send_webhook(slack_url, sneaker_url, picture_url, model, brand, referenceCode, \
	value, currency, month, day, hour, time_zone, min_size, max_size, country):
	slack = Slack(url=slack_url)
	slack.post(text="Raffle Monitor",
	    blocks = [
			{
				"type": "section",
				"text": {
					"type": "mrkdwn",
					"text": ":athletic_shoe: <" + sneaker_url + "|" + model + ">\
					\n:shopping_bags: " + brand + "\
					\n:label: " + referenceCode + "\
					\n:moneybag: " + value + " " + currency + "\
					\n:date: " + month + " " + day + " @ " + hour + ":00 " + time_zone + "\
					\n:straight_ruler: " + min_size + " - " + max_size + " " + country
				},
				"accessory": {
					"type": "image",
					"image_url": picture_url,
					"alt_text": model
				}
			},
			{
				"type": "divider"
			}
		]
	)


# main_url and slack_url could be passed as command line parameters
# to make encapsulate its behaviour.
main_url = 'https://releases.43einhalb.com/en/'
slack_url = ''

riffled_sneakers = []

while (True):
	main_response = get_url_response(main_url)
	if response_is_200(main_response):
		main_tree = get_html_tree(main_response)
		open_raffles = get_list_of_open_raffles(main_tree)
		for sneaker in open_raffles:
			sibling = get_sibling_element(sneaker, '.', 'div', 'class', 'product-image mb-2 mb-md-3 bg-gray-100')
			sneaker_url = get_sneaker_raffle_url(sibling)
			if sneaker_url not in riffled_sneakers:
				riffled_sneakers.append(sneaker_url)
				sneaker_response = get_url_response(sneaker_url)
				if response_is_200(sneaker_response):
					sneaker_tree = get_html_tree(sneaker_response)
					picture_url = get_picture(sneaker_tree)
					model, brand, referenceCode = get_model_brand_referenceCode(sneaker_tree)
					value, currency = get_price(sneaker_tree)
					month, day, hour, time_zone = get_closing_date(sneaker_tree)
					min_size, max_size, country = get_sizes(sneaker_tree)
					send_webhook(slack_url, sneaker_url, picture_url, model, brand, \
						referenceCode, value, currency, month, day, hour, time_zone, min_size, max_size, country)
				else:
					sneaker_response.raise_for_status()
		sleep(10)
	else:
		main_response.raise_for_status()
