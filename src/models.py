from collections import Counter
import datetime


class Category:
    def __init__(self, title, url, topics=[], load_id=None):
        self.title = title
        self.url = url
        self.topics = topics
        self.load_id = load_id

    def __getstate__(self):
        return {"id": id(self), "title": self.title, "url": self.url, "topics": [id(topic) for topic in self.topics]}


class Topic:
    def __init__(self, category, title, url, posts=None, author=None, load_id=None):
        self.author = author
        self.category = category
        self.title = title
        self.url = url
        if posts is None:
            self.posts = []
        else:
            self.posts = posts
        if load_id is not None:
            self.load_id = load_id

    def __getstate__(self):
        return {
            "id": id(self),
            "author": id(self.author) if self.author else None,
            "category": id(self.category),
            "title": self.title,
            "url": self.url,
            "posts": [id(post) for post in self.posts],
        }


class Post:
    def __init__(self, topic, author, content, timestr, category=None, load_id=None, pre_compute_done=False, words=None, word_count=None):
        self.topic = topic
        if category is not None:
            self.category = category
        elif self.topic is not None and self.topic.category is not None:
            self.category = self.topic.category
        else:
            self.category = None
        self.author = author
        self.datetime = datetime.datetime.strptime(timestr, "%B %d, %Y, %I:%M %p")
        self.content = content
        if load_id is not None:
            self.load_id = load_id

        # for pre-compute later:
        self.pre_compute_done = False
        self.words = None
        self.word_count = None

    def __getstate__(self):
        return {
            "id": id(self),
            "topic": id(self.topic) if self.topic else None,
            "category": id(self.category) if self.category else None,
            "author": id(self.author) if self.author else None,
            "datetime": self.datetime.strftime("%B %d, %Y, %I:%M %p"),
            "content": self.content,
            "pre_compute_done": self.pre_compute_done,
            "words": self.words,
            "word_count": self.word_count,
        }

    def pre_compute(self):
        if self.pre_compute_done:
            return
        chars = set("?/!-.,\":;\'()[]{}<>/\\|@#$%^&*_+=~`")
        replace_chars = ["\n", "\\n", "\t", "\\t", "\r", "\\r"] + list(chars) + ["   ", "  "]
        content = self.content.lower()
        words = content.split()
        words = [word for word in words if "https" not in word and ".com" not in word]
        content = " ".join(words)

        for char in replace_chars:
            content = content.replace(char, " ")
        self.words = Counter(content.split())
        self.word_count = sum(self.words.values())
        self.pre_compute_done = True


class Author:
    def __init__(self, name, posts=[], new_threads=[], load_id=None):
        self.name = name
        self.posts = posts
        self.new_threads = new_threads
        self.load_id = load_id

    def __getstate__(self):
        return {
            "id": id(self),
            "name": self.name,
            "posts": [id(post) for post in self.posts],
            "new_threads": [id(thread) for thread in self.new_threads],
        }


class leaderboard:
    def __init__(self, title, headers, data):
        self.title = title
        self.headers = headers
        self.data = data
        self.id = hash(title)
