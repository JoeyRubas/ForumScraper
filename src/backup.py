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
        print("File found. Loading data from backup.")
        with open(file_name, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Reconstruct objects. Use load_id to restore associations later
        categories = {category["load_id"]: Category(category["title"], category["url"], topics=category["topics"]) for category in data["categories"]}
        topics = {
            topic["load_id"]: Topic(topic["category"], topic["title"], topic["url"], author=topic["author"], posts=topic["posts"])
            for topic in data["topics"]
        }
        posts = {
            post["load_id"]: Post(
                post["topic"],
                post["author"],
                post["content"],
                post["datetime"][0],
                category=post["category"],
                pre_compute_done=post["pre_compute_done"],
                words=post["words"],
                word_count=post["word_count"],
            )
            for post in data["posts"]
        }
        authors_by_id = {
            author["load_id"]: Author(author["name"], author["url"], posts=author["posts"], new_threads=author["new_threads"])
            for author in data["authors"]
        }
        authors = {author.name: author for author in authors_by_id.values()}

        # Restore associations using load_id
        for category in categories.values():
            category.topics = set(topics[load_id] for load_id in category.topics)
        for topic in topics.values():
            topic.category = categories[topic.category]
            topic.posts = set(posts[load_id] for load_id in topic.posts)
            topic.author = authors_by_id[topic.author]
        for post in posts.values():
            post.topic = topics[post.topic]
            post.category = categories[post.category]
            post.author = authors_by_id[post.author]
        for author in authors.values():
            author.posts = set(posts[load_id] for load_id in author.posts)
            author.new_threads = set(topics[load_id] for load_id in author.new_threads)

        print("Data loaded successfully.")
        return categories.values(), topics.values(), posts.values(), authors
    return False
