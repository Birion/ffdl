from re import sub, match
from typing import List, Tuple

import attr
from bs4 import BeautifulSoup, Tag
from furl import furl
from requests import Response

from pyffdl.sites.story import Story
from pyffdl.utilities.misc import clean_text


@attr.s
class HTMLStory(Story):
    chapters: List[str] = attr.ib()
    author: str = attr.ib()
    title: str = attr.ib()

    @staticmethod
    def get_raw_text(page: Response) -> str:
        """
        Returns only the text of the chapter
        """

        text = BeautifulSoup(page.text, "html5lib")
        text = sub(r"(\n|\r|\s)+", " ", str(text))
        text = sub(r"\s*(</?p>)\s*", r"\1", text)
        text = sub(r"<br/?>", "</p><p>", text)
        text = sub(r"<p>\s*</p>", "", text)

        return clean_text(
            [
                x
                for x in BeautifulSoup(text, "html5lib").find("body")("p")
                if not match(r"^\s*<p>\s*</p>\s*$", str(x))
            ]
        )

    def get_chapters(self) -> None:
        """
        Gets the number of chapters and the base template for chapter URLs
        """

        def _parse_url(url: str) -> Tuple[furl, str]:
            _url = furl(url)
            _file = _url.path.segments[-1]
            _name = _file.split(".")[0] if "." in _file else _file
            return _url, _name.capitalize()

        self._metadata.chapters = [_parse_url(x) for x in self.chapters]

    def make_title_page(self) -> None:
        """
        Parses the main page for information about the story and author.
        """
        self._metadata.title = self.title
        self._metadata.author.name = self.author
        self._metadata.author.url = None
        self._metadata.language = "English"
        self.url = None

        clean_title = sub(rf"{self.ILLEGAL_CHARACTERS}", "_", self._metadata.title)
        self._filename = f"{self._metadata.author.name} - {clean_title}.epub"

    def make_new_chapter_url(self, url: furl, value: str) -> furl:
        return furl(value)
