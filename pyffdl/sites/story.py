from datetime import date
from io import BytesIO
from pathlib import Path
from re import sub
from sys import exit
from typing import Iterator, List, Tuple, Union
from uuid import uuid4

import attr
import pendulum
from bs4 import BeautifulSoup, Tag
from click import echo, style
from ebooklib.epub import EpubBook, EpubHtml, EpubItem, EpubNav, EpubNcx, write_epub
from furl import furl
from iso639 import to_iso639_1
from mako.template import Template
from requests import Response, Session, codes

from pyffdl.utilities.covers import Cover
from pyffdl.utilities.misc import strlen


@attr.s
class Author:
    name: str = attr.ib(factory=str)
    url: furl = attr.ib(factory=furl)


@attr.s
class Metadata:
    url: furl = attr.ib(factory=furl, converter=furl)
    title: str = attr.ib(factory=str)
    author: Author = attr.ib(factory=Author)
    complete: bool = attr.ib(default=False)
    published: date = attr.ib(default=pendulum.local(1970, 1, 1))
    updated: date = attr.ib(default=pendulum.local(1970, 1, 1))
    language: str = attr.ib(factory=str)
    category: str = attr.ib(factory=str)
    genres: List[str] = attr.ib(factory=list)
    characters: List[str] = attr.ib(factory=list)
    words: int = attr.ib(default=0)
    summary: str = attr.ib(factory=str)
    rating: str = attr.ib(factory=str)
    tags: List[str] = attr.ib(factory=list)
    chapters: List[str] = attr.ib(factory=list)


@attr.s
class Story:
    url: furl = attr.ib(validator=attr.validators.instance_of(furl), converter=furl)

    _metadata: Metadata = attr.ib(init=False, default=Metadata(url))
    _datasource: Path = attr.ib(
        init=False, default=(Path(__file__) / ".." / ".." / "data").resolve()
    )
    _filename: str = attr.ib(init=False, default=None)
    _session: Session = attr.ib(init=False, factory=Session)
    _styles: List[str] = attr.ib(init=False, default=["style.css"])
    _main_page: BeautifulSoup = attr.ib(init=False)
    _chapter_select: str = attr.ib(init=False)

    ILLEGAL_CHARACTERS = r'[<>:"/\|?]'

    def _initialise_main_page(self):
        main_page_request = self._session.get(self.url)
        if main_page_request.status_code != codes.ok:
            exit(1)
        self._main_page = BeautifulSoup(main_page_request.content, "html5lib")

    def run(self):
        self._initialise_main_page()
        self.make_title_page()
        self.get_chapters()
        self.make_ebook()

    def prepare_style(self, filename: str) -> EpubItem:
        cssfile = self._datasource / filename
        with cssfile.open() as fp:
            return EpubItem(
                uid=cssfile.stem,
                file_name=f"style/{cssfile.name}",
                media_type="text/css",
                content=fp.read(),
            )

    @property
    def styles(self):
        return [self.prepare_style(file) for file in self._styles]

    @staticmethod
    def get_raw_text(page: Response) -> str:
        """
        Returns only the text of the chapter
        """
        pass

    @staticmethod
    def chapter_parser(value: Tag) -> Union[str, Tuple[int, str]]:
        return sub(r"\d+\.\s+", "", value.text)

    def get_chapters(self) -> None:
        """
        Gets the number of chapters and the base template for chapter URLs
        """
        list_of_chapters = self._main_page.select(self._chapter_select)

        if list_of_chapters:
            self._metadata.chapters = [self.chapter_parser(x) for x in list_of_chapters]
        else:
            self._metadata.chapters = [self._metadata.title]

    def make_title_page(self) -> None:
        """
        Parses the main page for information about the story and author.
        """
        pass

    def make_new_chapter_url(self, url: furl, value: int) -> furl:
        """
        Update base url with next chapter format.
        """
        pass

    def step_through_chapters(self) -> Iterator[EpubHtml]:
        """
        Runs through the list of chapters and downloads each one.
        """

        chap_padding = (
            strlen(self._metadata.chapters)
            if strlen(self._metadata.chapters) > 2
            else 2
        )

        for index, title in enumerate(self._metadata.chapters):
            try:
                url_segment, title = title
            except ValueError:
                url_segment = index + 1
            url = self.make_new_chapter_url(self.url.copy(), url_segment)
            header = f"<h1>{title}</h1>"
            raw_chapter = self._session.get(url)
            text = header + self.get_raw_text(raw_chapter)
            chapter_number = str(index + 1).zfill(chap_padding)
            echo(
                f"Downloading chapter {style(chapter_number, bold=True, fg='blue')} - {style(title, fg='yellow')}"
            )
            chapter = EpubHtml(
                title=title,
                file_name=f"chapter{chapter_number}.xhtml",
                content=text,
                uid=f"chapter{chapter_number}",
            )
            for s in self.styles:
                chapter.add_item(s)
            yield chapter

    def make_ebook(self) -> None:
        """
        Combines everything to make an ePub book.
        """
        book = EpubBook()
        book.set_identifier(str(uuid4()))
        book.set_title(self._metadata.title)
        book.set_language(to_iso639_1(self._metadata.language))
        book.add_author(self._metadata.author.name)

        nav = EpubNav()

        book.add_item(EpubNcx())
        book.add_item(nav)

        book.toc = [x for x in self.step_through_chapters()]

        with BytesIO() as b:
            cover = Cover.create(
                self._metadata.title, self._metadata.author.name, self._datasource
            )
            cover.run()
            cover.image.save(b, format="jpeg")
            book.set_cover("cover.jpg", b.getvalue())

        template = Template(filename=str(self._datasource / "title.mako"))

        title_page = EpubHtml(
            title=self._metadata.title,
            file_name="title.xhtml",
            uid="title",
            content=template.render(story=self._metadata),
        )

        for s in self.styles:
            title_page.add_item(s)
            book.add_item(s)
        book.add_item(title_page)

        book.spine = ["cover", title_page]

        for c in book.toc:
            book.add_item(c)
            book.spine.append(c)

        book.spine.append(nav)

        self._write(book)

    def _write(self, book) -> None:
        """
        Create the epub file.
        """
        echo("Writing into " + style(self._filename, bold=True, fg="green"))
        write_epub(self._filename, book, {"tidyhtml": True, "epub3_pages": False})
