import os
from string import Formatter
import requests
from bs4 import BeautifulSoup
from models import Category, Topic, Post, Author
from backup import load_data, save_data, read_or_call_url


def scrape():
    values = load_data()
    if values:
        categories, topics, posts, authors = values
        print("Skipping scraping. Data already loaded.")
        return categories, topics, posts, authors
    categories = []
    topics = []
    posts = []
    authors = {}
    session = requests.Session()
    login_url = "https://apda.online/wp-login.php?loggedout=true&wp_lang=en_US"
    # Get username and password from .env
    payload = {"log": os.getenv("USERNAME"), "pwd": os.getenv("PASSWORD")}
    response = session.post(login_url, data=payload)
    soup = BeautifulSoup(response.text, "html.parser")
    categories_soup = BeautifulSoup(session.get("https://apda.online/forum/").text, "html.parser")
    categories_soup = soup.find_all("a", class_="forum-title")
    categories = [Category(category.text, category["href"]) for category in categories_soup]

    seen = set()
    queue = set()

    for category in categories:
        seen.add(category.url)
        queue.add(category.url)
        while queue:
            url = queue.pop()
            soup = read_or_call_url(session, url)
            topic_soup = soup.find_all("div", class_="topic-name")
            for topic in topic_soup:
                t = Topic(category, topic.a.text, topic.a["href"])
                category.topics.append(t)
                topics.append(t)
            next_page = soup.find("div", class_="pages-and-menu")
            pages = next_page.find("div", class_="pages")
            if pages:
                new_urls = set(a["href"] for a in pages.find_all("a", href=True)) - seen
                seen.update(new_urls)
                queue.update(new_urls)

    for topic in topics:
        print("Scraping", topic.title)
        seen.add(topic.url)
        queue.add(topic.url)
        while queue:
            url = queue.pop()
            soup = read_or_call_url(session, url)
            post_soup = soup.find_all("div", class_="post-element")
            if topic.author is None and post_soup and "first-post" in post_soup[0].get("class", []):
                author_name = post_soup[0].find("a", class_="profile-link").text
                if author_name not in authors:
                    authors[author_name] = Author(author_name)
                topic.author = authors[author_name]

            for post in post_soup:
                date_item = post.find("div", class_="forum-post-date")
                if date_item is None:
                    continue
                date = date_item.text
                content = post.find("div", class_="post-message")
                content_text = "/n".join([p.text for p in content.find_all("p")])
                author_name = post.find("a", class_="profile-link")
                if author_name is not None:
                    author_name = author_name.text
                else:
                    author_name = "deleted"
                if author_name not in authors:
                    authors[author_name] = Author(author_name)
                author = authors[author_name]
                p = Post(topic, author, str(content_text), date)
                topic.posts.append(p)
                posts.append(p)
            next_page = soup.find("div", class_="pages-and-menu")
            pages = next_page.find("div", class_="pages")
            if pages:
                new_urls = set(a["href"] for a in pages.find_all("a", href=True)) - seen
                seen.update(new_urls)
                queue.update(new_urls)
    save_data(categories, topics, posts, authors)
    return categories, topics, posts, authors
