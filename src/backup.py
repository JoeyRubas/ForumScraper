import os
import json
from string import Formatter
from bs4 import BeautifulSoup
from models import Category, Topic, Post, Author


def save_data(categories, topics, posts, authors, file_name="scraped_data.txt"):
    data = {
        "categories": [category.__getstate__() for category in categories],
        "topics": [topic.__getstate__() for topic in topics],
        "posts": [post.__getstate__() for post in posts],
        "authors": [author.__getstate__() for author in authors.values()],
    }
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print("Data saved successfully.")


def load_data(file_name="scraped_data.txt"):
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Reconstruct objects. Use load_id to restore associations later
        categories = {category["id"]: Category(category["title"], category["url"], topics=category["topics"]) for category in data["categories"]}
        topics = {
            topic["id"]: Topic(topic["category"], topic["title"], topic["url"], author=topic["author"], posts=topic["posts"])
            for topic in data["topics"]
        }
        posts = {
            post["id"]: Post(
                post["topic"],
                post["author"],
                post["content"],
                post["datetime"],
                category=post["category"],
                pre_compute_done=post["pre_compute_done"],
                words=post["words"],
                word_count=post["word_count"],
            )
            for post in data["posts"]
        }
        authors_by_id = {author["id"]: Author(author["name"], posts=author["posts"], new_threads=author["new_threads"]) for author in data["authors"]}
        authors = {author.name: author for author in authors_by_id.values()}

        # Restore associations using load_id
        for category in categories.values():
            category.topics = [topics[load_id] for load_id in category.topics]
        for topic in topics.values():
            topic.category = categories[topic.category]
            topic.posts = [posts[load_id] for load_id in topic.posts]
            topic.author = authors_by_id[topic.author]
        for post in posts.values():
            post.topic = topics[post.topic]
            post.category = categories[post.category]
            post.author = authors_by_id[post.author]
        for author in authors.values():
            author.posts = [posts[load_id] for load_id in author.posts]
            author.new_threads = [topics[load_id] for load_id in author.new_threads]

        print("Data loaded successfully.")
        return categories.values(), topics.values(), posts.values(), authors
    return False


def read_or_call_url(session, url, save_dir="backup"):
    # Create a file path based on the URL
    file_name = url.replace("https://", "").replace("/", "_").replace("?", "_q_") + ".html"
    file_path = os.path.join(save_dir, file_name)

    # Check if the file already exists
    if os.path.exists(file_path):
        # print(f"Loading from saved file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as file:
            return BeautifulSoup(file.read(), "html.parser")

    # Fetch the URL if not already saved
    # print(f"Fetching and saving: {url}")
    response = session.get(url)
    os.makedirs(save_dir, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(response.text)
    return BeautifulSoup(response.text, "html.parser")
