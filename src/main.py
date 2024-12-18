import cProfile
from contextlib import redirect_stdout

from concurrent.futures import ThreadPoolExecutor
from backup import save_data
from scraper import scrape
from stats import calculate_stats, print_stats, render_to_file
import os

os.environ['PYTHONUTF8'] = '1'


def main(force_scrape=False, save_after_pre_compute=False):
    force_scrape = False
    force_pre_compute = False
    save_after_pre_compute = False
    print("Starting scraping...")
    categories, topics, posts, authors = scrape(force_scrape=force_scrape)

    print("Pre-computing statistics...")
    for post in posts:
        post.pre_compute(force_pre_compute=force_pre_compute)
    # Save is called automatically in scrape, this is to save the pre-computed data (optional)
    if save_after_pre_compute:
        save_data(categories, topics, posts, authors)

    # Thread function to calculate stats
    def calculate_wrapper(*args, **kwargs):
        return calculate_stats(*args, **kwargs)

    # Use ThreadPoolExecutor for parallel stat calculation
    with ThreadPoolExecutor() as executor:
        future_include_fun_games = executor.submit(calculate_wrapper, categories)
        future_exclude_fun_games = executor.submit(calculate_wrapper, categories, exclude_categories=["Fun & Games"])
        future_just_general = executor.submit(calculate_wrapper, categories, include_categories=["General"])

        include_fun_games_stats = future_include_fun_games.result()
        exclude_fun_games_stats = future_exclude_fun_games.result()
        just_general = future_just_general.result()

    output_file = "forum_summary.txt"
    with open(output_file, "w", encoding="utf8") as f:
        with redirect_stdout(f):
            print_stats(include_fun_games_stats, "Forum Leaderboard Including 'Fun & Games'")
            print_stats(exclude_fun_games_stats, "Forum Leaderboard Excluding 'Fun & Games'")
            print_stats(just_general, "Forum Leaderboard for Just 'General' Category")

        render_to_file(
            "stats.html",
            "all_categories.html",
            title="Leaderboards for All Categories (Including 'Fun & Games')",
            summary=include_fun_games_stats["summary"],
            leaderboards=include_fun_games_stats["leaderboards"],
            print_len=25,
        )

        render_to_file(
            "stats.html",
            "exclude_games.html",
            title="Leaderboards for All Categories (Excluding 'Fun & Games')",
            summary=exclude_fun_games_stats["summary"],
            leaderboards=exclude_fun_games_stats["leaderboards"],
            print_len=25,
        )

        render_to_file(
            "stats.html",
            "just_general.html",
            title="Leaderboards for General",
            summary=just_general["summary"],
            leaderboards=just_general["leaderboards"],
            print_len=25,
        )

        render_to_file("index.html", "index.html", root="", title="Forum Leaderboards Home")


if __name__ == "__main__":
    main()
