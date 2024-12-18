import os
import requests
from bs4 import BeautifulSoup
from models import Category, Topic, Post, Author
from backup import load_data, save_data
import heapq


class pageWrapper:
    def __init__(self, url, category=None, topic=None):
        self.url = url
        self.category = category
        self.topic = topic

    def __eq__(self, other):
        if isinstance(other, pageWrapper):
            return self.url == other.url
        return False

    def __hash__(self):
        return hash(self.url)


def get_or_create_author(author_element, authors):
    author_name = author_element.text if author_element is not None else "deleted"
    if author_name not in authors:
        authors[author_name] = Author(author_name, author_element["href"])
    return authors[author_name]


def search_page(page, session, data, tracker):
    soup, from_web = read_or_call_url(session, page.url)
    tracker.scraped += 1
    if from_web:
        tracker.from_web += 1
    else:
        tracker.from_backup += 1
    new_high, new_low = set(), set()
    if page.topic is None:
        new_high.update(find_next_page(soup, data, page))
    else:
        new_low.update(find_next_page(soup, data, page))
    new_high.update(find_categories(soup, data, page))
    if page.category is not None:
        new_low.update(find_topics(soup, data, page))
    if page.topic is not None:
        find_posts(soup, data, page)
    return new_high, new_low


def find_categories(soup, data, page):
    categories_soup = soup.find_all("a", class_="forum-title")
    new_pages = set()
    for category in categories_soup:
        c_obj = Category(category.text, category["href"])
        data["categories"].add(c_obj)
        new_pages.add(pageWrapper(category["href"], category=c_obj))
    return new_pages


def find_topics(soup, data, page):
    category = page.category
    topic_soup = soup.find_all("div", class_="topic-name")
    new_pages = set()
    for topic in topic_soup:
        t = Topic(category, topic.a.text, topic.a["href"])
        category.topics.add(t)
        data["topics"].add(t)
        new_pages.add(pageWrapper(topic.a["href"], category=category, topic=t))
    return new_pages


def find_posts(soup, data, page):
    topic = page.topic
    authors = data["authors"]
    post_soup = soup.find_all("div", class_="post-element")

    # Manage post and topic authors
    if topic.author is None and post_soup and "first-post" in post_soup[0].get("class", []):
        author_element = post_soup[0].find("a", class_="profile-link")
        author = get_or_create_author(author_element, authors)
        topic.author = author
        author.new_threads.add(topic)

    for post in post_soup:
        date_item = post.find("div", class_="forum-post-date")
        if date_item is None:
            continue
        date = date_item.text
        content = post.find("div", class_="post-message").text
        author = get_or_create_author(post.find("a", class_="profile-link"), authors)
        p = Post(topic, author, content, date)
        author.posts.add(p)
        if p.content == "":
            print("here!")
        elif not isinstance(p.content, str):
            print("here!")
        topic.posts.add(p)
        data["posts"].add(p)


def find_next_page(soup, data, page):
    new_pages = set()
    next_page = soup.find("div", class_="pages-and-menu")
    if next_page is not None:
        pages = next_page.find("div", class_="pages")
        if pages is not None:
            for a in pages.find_all("a", href=True):
                category = page.category if page.category is not None else page.topic.category
                topic = page.topic if page.topic is not None else None
                new_pages.add(pageWrapper(a["href"], category=category, topic=topic))
    return new_pages


def printProgressBar(iteration, total, prefix="", suffix="", decimals=1, length=50, fill="█"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + "-" * (length - filledLength)

    # Clear only the lines that are printed
    print("\033[F\033[K" * 3, end="")  # Clear up to three lines

    # Reprint progress
    print(prefix)
    print(f"|{bar}| {percent}%")
    print(suffix)

    # Finish with a newline when done
    if iteration == total:
        print()


def read_or_call_url(session, url, save_dir="backup"):
    # Create a file path based on the URL
    file_name = url.replace("https://", "").replace("/", "_").replace("?", "_q_") + ".html"
    file_path = os.path.join(save_dir, file_name)

    # Check if the file already exists
    if os.path.exists(file_path):
        # print(f"Loading from saved file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as file:
            return BeautifulSoup(file.read(), "html.parser"), False

    # Fetch the URL if not already saved
    # print(f"Fetching and saving: {url}")
    response = session.get(url)
    os.makedirs(save_dir, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(response.text)
    return BeautifulSoup(response.text, "html.parser"), True


class scrapeTracker:
    def __init__(self):
        self.scraped = 0
        self.from_web = 0
        self.from_backup = 0


def scrape(force_scrape=False):
    if not force_scrape:
        values = load_data()
        if values:
            categories, topics, posts, authors = values
            print("Skipping scraping. Data already loaded.")
            return categories, topics, posts, authors
    data = {"categories": set(), "topics": set(), "posts": set(), "authors": {"deleted": Author("deleted", None)}}
    session = requests.Session()
    login_url = "https://apda.online/wp-login.php?loggedout=true&wp_lang=en_US"
    response = session.post(login_url, data={"log": os.getenv("USERNAME"), "pwd": os.getenv("PASSWORD")})
    if response.status_code != 200:
        print("Login failed. Exiting.")
        return
    seen = set()
    queue_high = []
    queue_low = []
    queue_high.append(pageWrapper("https://apda.online/forum/"))
    tracker = scrapeTracker()
    print("\n\n\n")
    while queue_high or queue_low:
        if queue_high:
            page = queue_high.pop(0)
        else:
            page = queue_low.pop(0)
        if page in seen:
            continue
        seen.add(page)
        new_high, new_low = search_page(page, session, data, tracker)
        new_high -= seen
        new_low -= seen
        queue_high.extend(new_high)
        queue_low.extend(new_low)
        scrape_str = f"{page.category.title if page.category else ''} {page.topic.title if page.topic else ''}"
        scrape_str = scrape_str[:50] + "..." if len(scrape_str) > 50 else scrape_str + " " * (53 - len(scrape_str))

        printProgressBar(
            tracker.scraped,
            tracker.scraped + len(queue_high) + len(queue_low) + 1,
            prefix=f"Scraped {tracker.from_web} From web and {tracker.from_backup} from backup. {len(queue_high)+len(queue_low)} (+{len(new_high)+len(new_low)}) discovered pages remaining.",
            suffix=f"Scraping {scrape_str}",
            length=50,
        )

    print("Done scraping!")
    save_data(**data)
    return data["categories"], data["topics"], data["posts"], data["authors"]
