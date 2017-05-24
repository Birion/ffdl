from datetime import date
from re import sub, compile
from sys import exit

from bs4 import BeautifulSoup
from click import echo
from requests import get, Response

from ffdl.story import Story
from ffdl.misc import dictionarise, in_dictionary


class FanFictionNetStory(Story):
    def __init__(self, url: str) -> None:
        super(FanFictionNetStory, self).__init__(url)

    @staticmethod
    def get_story(page: Response) -> str:
        """
        Returns only the text of the chapter
        """

        return "".join([
            sub(r"\s+", " ", str(x).strip()) for x
            in BeautifulSoup(page.content, "html5lib").find("div", class_="storytext").contents
        ])

    def get_chapters(self) -> None:
        """
        Gets the number of chapters and the base template for chapter URLs
        """
        list_of_chapters = self.main_page.find("select", id="chap_select")

        if list_of_chapters:
            self.chapter_titles = [sub(r"\d+\. ", "", x.string) for x in list_of_chapters("option")]
        else:
            self.chapter_titles = [self.title]

    def make_title_page(self) -> None:
        """
        Parses the main page for information about the story and author.
        """
        _header = self.main_page.find(id="profile_top")
        _author = _header.find("a", href=compile(r"^/u/\d+/"))
        _data = dictionarise([x.strip() for x in " ".join(_header.find(class_="xgray").stripped_strings).split(" - ")])

        echo(_data)

        published = in_dictionary(_data, "Published")
        updated = in_dictionary(_data, "Updated")

        def check_date(input_date: str) -> date:
            if not input_date:
                return date(1970, 1, 1)
            if "m" in input_date or "h" in input_date:
                return date.today()
            story_date = [int(x) for x in input_date.split("/")]
            if len(story_date) == 2:
                story_date.append(date.today().year)
            return date(story_date[2], story_date[0], story_date[1])

        self.title = _header.find("b").string
        self.author["name"] = _author.string
        self.author["url"] = self.main_url.copy().set(path=_author["href"])
        self.summary = _header.find("div", class_="xcontrast_txt").string
        self.rating = in_dictionary(_data, "Rated")
        self.category = self.main_page.find(id="pre_story_links").find("a").string
        self.genres = in_dictionary(_data, "Genres")
        self.characters = in_dictionary(_data, "Characters")
        self.words = in_dictionary(_data, "Words")
        self.published = check_date(published)
        self.updated = check_date(updated)
        self.language = in_dictionary(_data, "Language")
        self.complete = in_dictionary(_data, "Status")