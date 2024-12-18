from collections import Counter, defaultdict
from string import Formatter
from tabulate import tabulate
from models import Author, Topic, leaderboard
from jinja2 import Environment, FileSystemLoader
import os

MIN_POSTS = 3
AUTHOR_PRINT_LEN = 25
TOPIC_PRINT_LEN = 10


def strfdelta(remainder, fmt="{D:02.0f}d {H:02.0f}h {M:02.0f}m", inputtype="timedelta"):
    f = Formatter()
    desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
    possible_fields = ("Y", "W", "D", "H", "M", "S")
    constants = {"Y": 31536000, "W": 604800, "D": 86400, "H": 3600, "M": 60, "S": 1}
    values = {}
    for field in possible_fields:
        if field in desired_fields and field in constants:
            (values[field], remainder) = divmod(remainder, constants[field])
    return f.format(fmt, **values)


def calculate_stats(categories, include_categories=[], exclude_categories=[]):
    # ====== Helper Functions ======
    def data(type, func, cond=lambda x: True):
        if type == "a":
            l = authors
        elif type == "t":
            l = ftopics
        return sorted([[i, func(i)] for i in l if cond(i)], key=lambda x: -x[1])

    def topic_time_span(topic):
        posts = [p for p in topic.posts]
        sorted_posts = sorted(posts, key=lambda post: post.datetime)
        time = (sorted_posts[-1].datetime - sorted_posts[0].datetime).total_seconds() if len(posts) > 1 else 0
        return time

    # ====== Filtering Data ======
    print("\nCalculating statistics for leaderboard with conditions:")
    if include_categories:
        print(f"Only include: { ', '.join(include_categories) }")
        categories = filter(lambda c: c.title in include_categories, categories)
    elif exclude_categories:
        print(f"Exclude: {', '.join(exclude_categories)}")
        categories = filter(lambda c: c.title not in exclude_categories, categories)
    else:
        print("No category filters applied.")
    categories = set(categories)
    topics = set(t for c in categories for t in c.topics)
    posts = set(p for t in topics for p in t.posts)
    authors = {p.author for p in posts}

    # Can't be pre-computed becasue relies on filters
    ftopics = set()
    topic_word_counts = defaultdict(int)
    topic_word_lengths = defaultdict(float)
    topic_post_lengths = defaultdict(float)
    for t in topics:
        if len(t.posts) > MIN_POSTS:
            ftopics.add(t)
            topic_word_counts[t] = sum(val for p in t.posts for val in p.words.values())
            topic_word_lengths[t] = sum(len(w) * c for p in t.posts for w, c in p.words.items()) / topic_word_counts[t]
            topic_post_lengths[t] = sum(p.word_count for p in t.posts) / len(t.posts)

    author_posts = defaultdict(list)
    author_word_counts = defaultdict(int)
    author_word_lens = defaultdict(float)
    author_post_lens = defaultdict(float)
    for a in list(authors):
        post_count = len(a.posts)
        # pre-apply minimum membership filters, saves on computation time
        if post_count > MIN_POSTS:
            author_word_counts[a] = sum([p.word_count for p in a.posts])
            author_word_lens[a] = sum(len(w) * c for post in a.posts for w, c in post.words.items()) / author_word_counts[a]
            author_posts[a] = [p for p in a.posts]
            author_post_lens[a] = sum(p.word_count for p in author_posts[a]) / len(author_posts[a])
        else:
            authors.remove(a)

    print("Filtering complete.")
    # New logging, print len of each set
    print(f"Categories: {len(categories)}")
    print(f"Topics: {len(topics)}")
    print(f"Posts: {len(posts)}")
    print(f"Authors: {len(authors)}")
    # print len of topic and author special dicts
    print(f"Filtered Topics: {len(ftopics)}")
    print(f"Author Posts: {len(author_posts)}")
    print(f"Author Word Counts: {len(author_word_counts)}")
    print(f"Author Word Lengths: {len(author_word_lens)}")
    print(f"Author Post Lengths: {len(author_post_lens)}")
    print("Logging complete.")

    # ====== Summary Calculations ======
    total_topics = len(topics)
    total_posts = len(posts)
    total_words = sum(p.word_count for p in posts)
    avg_posts_per_topic = total_posts / total_topics
    avg_words_per_topic = total_words / total_topics
    avg_words_per_post = total_words / total_posts

    print("Summary Calculations complete.")
    # ====== Data for Authors ======
    aposts = data("a", lambda a: len(author_posts[a]))
    atopics = data("a", lambda a: len([t for t in a.new_threads if t in topics]))
    awords = data("a", lambda a: author_word_counts[a])
    aword_len = data("a", lambda a: author_word_lens[a])
    apost_len = data("a", lambda a: author_post_lens[a])
    aposts_by_topic = data("a", lambda a: len(author_posts[a]) / len({p.topic for p in author_posts[a]}))
    print("Author Calculations complete.")

    # ====== Data for Topics ======
    twords = data("t", lambda t: topic_word_counts[t])
    tposts = data("t", lambda t: len(t.posts))
    tauthors = data("t", lambda t: len({p.author for p in t.posts}))
    twordlen = data("t", lambda t: topic_word_lengths[t])
    tpostlen = data("t", lambda t: topic_post_lengths[t])
    ttime = data("t", topic_time_span)
    ttime = [[t[0], strfdelta(t[1])] for t in ttime]
    print("Topic Calculations complete.\n")

    # ====== Data for Words ======
    w_by_p = defaultdict(set)
    for p in posts:
        for w in p.words.keys():
            if len(w) > 10:
                w_by_p[w].add(p)
    lwords = sorted(
        [
            [
                ", ".join(f'<a href="{p.author.url}"> {p.author.name} </a>' for p in p_list),
                ", ".join(f'<a href="{p.topic.url}"> {p.topic.title} </a>' for p in p_list),
                w,
                len(w),
            ]
            for w, p_list in w_by_p.items()
        ],
        key=lambda x: -x[3],
    )

    leaderboards = [
        leaderboard("Most Topics by Author", ["Author", "Count"], atopics, AUTHOR_PRINT_LEN),
        leaderboard("Most Posts by Author", ["Author", "Count"], aposts, AUTHOR_PRINT_LEN),
        leaderboard("Most Words by Author", ["Author", "Count"], awords, AUTHOR_PRINT_LEN),
        leaderboard("Longest Avg Word by Author (Minimum 5 Posts)", ["Authors", "Word Length"], aword_len, AUTHOR_PRINT_LEN),
        leaderboard("Highest Avg Word per Post by Author (Minimum 5 Posts)", ["Author", "Word Count"], apost_len, AUTHOR_PRINT_LEN),
        leaderboard("Most Average Posts per Topic by Author", ["Author", "Avg Posts"], aposts_by_topic, AUTHOR_PRINT_LEN),
        leaderboard("Most Words by Topic", ["Topic", "Word Count"], twords, TOPIC_PRINT_LEN),
        leaderboard("Most Posts by Topic", ["Topic", "Post Count"], tposts, TOPIC_PRINT_LEN),
        leaderboard("Most Posters by Topic", ["Topic", "Author Count"], tauthors, TOPIC_PRINT_LEN),
        leaderboard(f"Longest Avg Word by Topic (Minimum {MIN_POSTS} Posts)", ["Topic", "Word Length"], twordlen, TOPIC_PRINT_LEN),
        leaderboard(f"Highest Avg Word per Post by Topic (Minimum {MIN_POSTS} Posts)", ["Topic", "Words Per Post"], tpostlen, TOPIC_PRINT_LEN),
        leaderboard("Longest Time Active by Topic", ["Topic", "Time Span"], ttime, TOPIC_PRINT_LEN),
        leaderboard("Longest Words", ["Authors", "Topics", "Words", "Length"], lwords, TOPIC_PRINT_LEN),
    ]

    # ====== Return the Results ======
    return {
        "summary": {
            "Total Topics": total_topics,
            "Total Posts": total_posts,
            "Total Words": total_words,
            "Avg Posts per Topic": avg_posts_per_topic,
            "Avg Words per Topic": avg_words_per_topic,
            "Avg Words per Post": avg_words_per_post,
        },
        "leaderboards": leaderboards,
    }


def nice_format(item):
    if isinstance(item, int):
        return f"{item:,.0f}"
    elif isinstance(item, float):
        return f"{item:,.2f}"
    elif isinstance(item, str):
        if item.isdigit():
            return f"{int(item):,.0f}"
        elif item.count(".") == 1 and item.replace(".", "").isdigit():
            return f"{float(item):,.2f}"
    elif isinstance(item, Author):
        return f"<a href='{item.url}'>{item.name}</a>"
    elif isinstance(item, Topic):
        return f"<a href='{item.url}'>{item.title}</a>"
    return item


def print_stats(stats, title):
    print(f"\n{'='*40}")
    print(f" {title} ")
    print(f"{'='*40}\n")

    print(tabulate(stats["summary"].items(), headers=["Metric", "Count"], tablefmt="fancy_grid", floatfmt=".0f"))
    print("\nLeaderboard Details:\n")
    for l in stats["leaderboards"]:
        print(l.title)
        for i, row in enumerate(l.data):
            for j, item in enumerate(row):
                l.data[i][j] = nice_format(item)
        table_data = [[i + 1, *row] for i, row in enumerate(l.data[: l.PRINT_LEN])]
        print(tabulate(table_data, headers=l.headers, tablefmt="fancy_grid"))
        print()


def render_to_file(template_name, output_file, root="web/pages/", **context):
    if "leaderboards" in context:
        for l in context["leaderboards"]:
            for i, row in enumerate(l.data):
                for j, item in enumerate(row):
                    l.data[i][j] = nice_format(item)

    env = Environment(loader=FileSystemLoader("web/templates"))
    template = env.get_template(template_name)
    output = template.render(**context)
    with open(f"{root}{output_file}", "w", encoding="utf8") as f:
        f.write(output)
