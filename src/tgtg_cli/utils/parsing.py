from typing import cast

from bs4 import BeautifulSoup, Tag

from tgtg_cli.utils.exceptions import UnexpectedResponse


class HTMLFormParser:

    def __init__(
        self,
        html: str,
        form_id: str,
        error_message: str | None = None,
    ) -> None:
        """
        Initializes the class. Loads the HTML into a BeautifulSoup object and
        parses the form with the given ID.
        """
        soup = BeautifulSoup(html, "html.parser")
        self._form = soup.find("form", attrs={"id": form_id})
        if self._form is None:
            raise UnexpectedResponse(error_message)

        # Other attributes
        self.error_message = error_message

    @property
    def form(self) -> Tag:
        if self._form is None:
            raise UnexpectedResponse(self.error_message)
        return self._form

    def parse_html_form_input(self, name: str) -> str:
        """
        Parses the value of input fields of an HTML form.

        Args:
            name (str): Name of the tag to parse.

        Raises:
            UnexpectedResponse: If the tag could not be parsed or doesn't have
                                an attribute 'value'.

        Returns:
            str: Value of the tag.
        """
        tag = self.form.find("input", attrs={"name": name})
        value = tag.get("value") if isinstance(tag, Tag) else None
        if value is None:
            raise UnexpectedResponse(
                self.error_message if self.error_message
                else "Unable to parse input values for HTML form."
            )
        return cast(str, value)
