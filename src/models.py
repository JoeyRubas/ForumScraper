from collections import Counter
import datetime
import hashlib


class ForumObject:
    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.load_id == other.load_id
        return False

    def __hash__(self):
        return int(self.load_id, 16)

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items()}


class Category(ForumObject):
    def __init__(self, title, url, topics=(), load_id=None):
        self.title = title
        self.url = url
        self.topics = set(topics)
        self.load_id = hashlib.sha1(url.encode()).hexdigest() if load_id is None else load_id

    def __getstate__(self):
        base = super().__getstate__()
        base["topics"] = [topic.load_id for topic in self.topics]
        return base


class Topic(ForumObject):
    def __init__(self, category, title, url, posts=(), author=None, load_id=None):
        self.author = author
        self.category = category
        self.title = title
        self.url = url
        self.posts = set(posts)
        self.load_id = hashlib.sha1(url.encode()).hexdigest() if load_id is None else load_id

    def __getstate__(self):
        base = super().__getstate__()
        base["author"] = self.author.load_id if self.author else None
        base["category"] = self.category.load_id
        base["posts"] = [post.load_id for post in self.posts]
        return base


class Post(ForumObject):
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
        self.load_id = hashlib.sha1(content.encode()).hexdigest() if load_id is None else load_id

        # for pre-compute later:
        self.pre_compute_done = False
        self.words = None
        self.word_count = None

    def __getstate__(self):
        base = super().__getstate__()
        base["topic"] = self.topic.load_id
        base["author"] = self.author.load_id
        base["category"] = self.category.load_id if self.category else None
        base["datetime"] = (self.datetime.strftime("%B %d, %Y, %I:%M %p"),)
        return base

    def pre_compute(self, force_pre_compute=False):
        if self.pre_compute_done and not force_pre_compute:
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


class Author(ForumObject):
    def __init__(self, name, url, posts=(), new_threads=(), load_id=None):
        self.name = name
        self.posts = set(posts)
        self.new_threads = set(new_threads)
        self.load_id = hashlib.sha1(name.encode()).hexdigest() if load_id is None else load_id
        self.url = url

    def __getstate__(self):
        base = super().__getstate__()
        base["posts"] = [post.load_id for post in self.posts]
        base["new_threads"] = [thread.load_id for thread in self.new_threads]
        return base


class leaderboard(ForumObject):
    def __init__(self, title, headers, data):
        self.title = title
        self.headers = headers
        self.data = data
        self.id = hashlib.sha1(title.encode()).hexdigest()
