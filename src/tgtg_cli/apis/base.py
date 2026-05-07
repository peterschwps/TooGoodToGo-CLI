import contextlib
import json
from urllib.parse import parse_qsl

import requests

from tgtg_cli.cli.config import Config
from tgtg_cli.utils.exceptions import RetryLimitReached, UnexpectedResponse
from tgtg_cli.utils.logging import get_logger


class BaseClient:

    def __init__(
        self,
        config: Config,
        headers: dict[str, str],
        proxy: str | None = None,
        timeout: int | float = 10,
    ):
        """
        Initializes a requests session.

        Args:
            config (Config): Instance of the Config class.
            headers (dict[str, str]): Headers to add to the session.
            proxy (str | None, optional): Proxy to add to the session.
                                          Defaults to None.
            timeout (int | float, optional): Request timeout to use when
                                             sending requests in seconds.
                                             Defaults to 10 seconds.
        """
        # Initialize session
        self.session = requests.Session()
        self.session.headers.update(headers)
        if proxy:
            self.session.proxies.update(
                {
                    "http": f"http://{proxy}",
                    "https": f"http://{proxy}",
                }
            )

        # Other attributes
        self._config = config
        self.timeout = timeout
        self.quit_on_failed_retry = False

        # Retrieve logger and overwrite send() method if logging is enabled
        if self._config.settings.application.enable_logging:
            self.logger = get_logger()
            self.session.send = self._send_with_logging
        else:
            self.logger = None

    def _get_body(
            self,
            request: requests.PreparedRequest | requests.Response,
        ) -> str | None:
        """
        Extracts and converts the body of a request to a string.
        Returns None if no body exists (or if the conversion is not supported -
        which shouldn't happen).

        Args:
            request (requests.PreparedRequest | requests.Response): Request or
                                                                    response to
                                                                    extract
                                                                    body from.

        Returns:
            str | None: Body of the request / response if it exists, else None.
        """
        # Check if body exists
        content_type = request.headers.get("Content-Type")
        if content_type:

            # Get body from request / response
            if isinstance(request, requests.PreparedRequest):
                body = request.body
            else:
                body = request.content

            # Convert body to dict (if possible)
            if (
                "application/json" in content_type.lower()
                and isinstance(body, bytes | bytearray)
            ):
                if isinstance(request, requests.PreparedRequest):
                    body = json.loads(body.decode("utf-8"))
                    body = json.dumps(body)
                else:
                    body = request.json()
                    body = json.dumps(body)
            elif (
                "form" in content_type.lower()
                and isinstance(body, bytes | bytearray)
            ):
                body = dict(parse_qsl(body.decode("utf-8")))
                body = json.dumps(body)
            else:
                body = None

            # Convert body to string if not set yet
            if not body and isinstance(request, requests.Response):
                body = request.text

            return body

        else:
            return None


    def _send_with_logging(
        self,
        request: requests.PreparedRequest,
        **kwargs,
    ) -> requests.Response:
        """
        Wrapper for the requests.Session.send() method. Implements logging of
        the request and response or possible errors.

        Args:
            request (requests.PreparedRequest): Request to send.

        Raises:
            e: Any error that occurs when calling requests.Session.send().

        Returns:
            requests.Response: Response of the request.
        """
        if self.logger is None:
            return requests.Session.send(self.session, request, **kwargs)

        # Log request
        body = self._get_body(request)
        self.logger.debug("")
        self.logger.debug(
            "%s %s-Request %s",
            "=" * 19,
            request.method,
            "=" * 19,
        )
        self.logger.debug("URL: %s", request.url)
        self.logger.debug("Headers: %s", json.dumps(dict(request.headers)))
        if body:
            self.logger.debug("Body: %s", body)
        self.logger.debug("")

        # Send request
        try:
            response = requests.Session.send(self.session, request, **kwargs)

        except Exception as e:
            self.logger.error(
                "%s Error for %s-Request %s",
                "=" * 14,
                request.method,
                "=" * 14,
            )
            self.logger.error("Error: %s", type(e).__name__)
            self.logger.error("Message: %s", str(e))
            self.logger.error("")
            raise e

        else:
            # Log response
            body = self._get_body(response)
            self.logger.debug("")
            self.logger.debug(
                "%s Response for %s-Request %s",
                "=" * 12,
                request.method,
                "=" * 12,
            )
            self.logger.debug("URL: %s", response.url)
            self.logger.debug(
                "Headers: %s",
                json.dumps(dict(response.headers))
            )
            if body:
                self.logger.debug("Body: %s", body)
            self.logger.debug("")
            return response

    def _handle_internal_errors(
        self,
        request: requests.PreparedRequest,
        response: requests.Response,
    ) -> tuple[bool, requests.Response | None]:
        """
        This method can be implemented in the child class to handle
        site-specific errors.
        Its return value determines if an UnexpectedResponse exception will
        be raised.

        Args:
            request (requests.PreparedRequest): Request to check for errors.
            response (requests.Response): Response of the latest request.

        Returns:
            tuple[bool,requests.Response | None]: True if an UnexpectedResponse
                                                  exception should be raised.
                                                  False to continue the _send()
                                                  method and have it return the
                                                  response of the request back
                                                  to the caller.
                                                  If a new response is
                                                  returned, it will replace the
                                                  previous response and be
                                                  returned to the caller.
                                                  Default is False, None.
        """
        _ = request, response
        return False, None

    def _update_prepared_request(
            self,
            request: requests.PreparedRequest,
    ) -> None:
        """
        Updates a prepared request (in-place) with the latest headers and
        cookies. Otherwise the headers will remain the same and the send()
        method of the session will keep using the old headers and cookies.

        This method should be called before re-sending a prepared request.

        Args:
            request (requests.PreparedRequest): Request to update.
        """
        # Update headers
        request.headers.clear()
        request.prepare_headers(self.session.headers)

        # Remove 'Cookie' header if it exists (otherwise it won't be updated
        # when using prepare_cookies()) and update headers with latest cookies
        with contextlib.suppress(KeyError):
            request.headers.pop("Cookie")
        request.prepare_cookies(self.session.cookies)

    def _send(
        self,
        request: requests.PreparedRequest,
        retry_limit: int = 3,
    ) -> requests.Response:
        """
        Sends a prepared request with retry and error handling.

        Args:
            request (requests.PreparedRequest): Prepared request to send.
            retry_limit (int, optional): Maximum number of retry attempts if a
                                         request fails.
                                         Defaults to 3 retries.

        Raises:
            RetryLimitReached: If the request fails for all retry attempts.
            UnexpectedResponse: If internal error handling signals that the
                                request was not successful.

        Returns:
            requests.Response: Response of the successful request.
        """
        # Check for general errors
        exception: Exception | None = None
        for _ in range(retry_limit):
            try:
                response = self.session.send(request, timeout=self.timeout)
                exception = None
                break

            # IMPORTANT: Keep order of except checks
            # Exception hierarchy: https://stackoverflow.com/a/76012327
            except requests.exceptions.InvalidURL as e:
                exception = e
                break  # to exit right away

            except requests.exceptions.RequestException as e:
                exception = e

        if exception:
            raise RetryLimitReached(
                f"Error when sending request: {exception}. Request: {request}."
            )

        # Check for site-specific errors
        # _handle_internal_errors() can be overridden in the child class
        raise_exception, new_response = self._handle_internal_errors(
            request=request,
            response=response,
        )
        if new_response:
            response = new_response

        if raise_exception:
            additional_notice = (
                " after failed retry" if self.quit_on_failed_retry else ""
            )
            raise UnexpectedResponse(
                f"Response{additional_notice} for {request.method}-request "
                f"to <{request.url}> [{response.status_code}]: "
                f"{response.text}"
            )
        else:
            self.quit_on_failed_retry = False
            return response

    def _get(self, *args, **kwargs) -> requests.Response:
        """
        Builds and sends a GET request.

        Returns:
            requests.Response: Response of the request.
        """
        request = self.session.prepare_request(
            requests.Request("GET", *args, **kwargs)
        )
        return self._send(request)

    def _post(
        self,
        *args,
        use_session_headers: bool = True,
        **kwargs,
    ) -> requests.Response:
        """
        Builds and sends a POST request.

        Args:
            use_session_headers (bool, optional): If True, uses the session to
                                                  prepare the request. This
                                                  adds the full configuration
                                                  of the session to the
                                                  request (headers, cookies,
                                                  proxy).
                                                  Defaults to True.

        Returns:
            requests.Response: Response of the request.
        """
        if use_session_headers:
            request = self.session.prepare_request(
                requests.Request("POST", *args, **kwargs)
            )
        else:
            request = requests.Request("POST", *args, **kwargs)
            request = request.prepare()
        return self._send(request)
