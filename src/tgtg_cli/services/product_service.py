import string
from datetime import datetime, time, timedelta
from time import sleep
from typing import Any, cast

from rich import box
from rich.table import Table

from tgtg_cli.apis.tgtg import TGTG
from tgtg_cli.cli import console
from tgtg_cli.cli.config import Config
from tgtg_cli.cli.types import Item, ItemResult
from tgtg_cli.services.order_service import OrderService
from tgtg_cli.utils.exceptions import SettingsError
from tgtg_cli.utils.models import ItemOverview
from tgtg_cli.utils.notifications import send_notification


class ProductService:
    def __init__(self, config: Config, tgtg: TGTG):
        self._config = config
        self._tgtg = tgtg

    def _get_item(
        self,
        latitude: float,
        longitude: float,
        item_id: str,
    ) -> ItemResult:
        """
        Retrieves the details for a specific item.

        Args:
            latitude (float): Latitude used as search origin.
            longitude (float): Longitude used as search origin.
            item_id (str): ID of the item to look up.

        Returns:
            ItemResult: Full details of the item.
        """
        item = self._tgtg.get_item(
            latitude=latitude,
            longitude=longitude,
            item_id=item_id,
        )
        return item

    def _get_items(
        self,
        latitude: float,
        longitude: float,
        radius: int,
        favorites_only: bool = False,
        search_phrase: str | None = None,
        sold_out_only: bool = False,
        with_stock_only: bool = False,
    ) -> list[ItemOverview]:
        """
        Retrieves items within a given radius from a given location. Allows
        filtering by favorites, search phrase, sold-out status and stock.

        Args:
            latitude (float): Latitude used as search origin.
            longitude (float): Longitude used as search origin.
            radius (int): Search radius in kilometers.
            favorites_only (bool, optional): If only favorites should be
                                             returned.
                                             Defaults to False.
            search_phrase (str | None, optional): Substring the display name
                                                  must contain.
                                                  Defaults to None.
            sold_out_only (bool, optional): If only sold-out items should be
                                            returned. This can be helpful when
                                            starting the monitoring process.
                                            Defaults to False.
            with_stock_only (bool, optional): If only in-stock items should be
                                              returned.
                                              Defaults to False.

        Returns:
            list[ItemOverview]: List of all items matching the criteria.
        """
        # Fetch favorites only if requested
        if favorites_only:
            items = self._get_favorite_items(latitude, longitude)

        else:
            # Fetch items from discover endpoint
            result = self._tgtg.discover(
                latitude=latitude,
                longitude=longitude,
                radius=radius,
            )

            # Flatten and de-duplicate the item buckets into a single list
            items: list[Item] = []
            seen: set[str] = set()
            for bucket in result["buckets"]:
                if bucket["bucket_type"] != "ITEM":
                    continue
                for item in bucket.get("items", []):
                    item_id = item["item"]["item_id"]
                    if item_id in seen:
                        continue
                    seen.add(item_id)
                    items.append(item)

        # Iterate over results and apply filters
        phrase = (search_phrase or "").casefold()

        all_items: list[ItemOverview] = []
        for item in items:
            available = item["items_available"]

            # Stock filters
            if sold_out_only and available != 0:
                continue
            if with_stock_only and available == 0:
                continue

            # Search phrase
            if phrase and phrase not in item["display_name"].casefold():
                continue

            # Create item overview
            price_minor_units = item["item"]["item_price"]["minor_units"]
            decimals = item["item"]["item_price"]["decimals"]
            all_items.append(
                ItemOverview(
                    id=item["item"]["item_id"],
                    name=item["display_name"],
                    price=round(price_minor_units / 10**decimals, 2),
                    currency_code=item["item"]["item_price"]["code"],
                    items_available=available,
                )
            )

        return all_items

    def _get_favorite_items(
        self,
        latitude: float,
        longitude: float,
    ) -> list[Item]:
        """
        Retrieves all favorite items.

        Args:
            latitude (float): Latitude used as search origin.
            longitude (float): Longitude used as search origin.

        Returns:
            list[Item]: All favorite items across all pages.
        """
        items: list[Item] = []
        page = 0

        # Iterate over all pages
        while True:
            result = self._tgtg.get_favorites(
                latitude=latitude,
                longitude=longitude,
                page=page,
            )
            items.extend(result["favourite_items"])
            paging = result["paging"]
            if page + 1 >= paging["total_pages"]:
                break
            page += 1
            sleep(1)  # to prevent rate limiting
        return items

    def _configure_filters(self) -> dict[str, Any]:
        """
        Configures various filter options.

        Returns:
            dict[str, Any]: All selected filter options.
        """
        custom_args = {}

        # Search phrase
        use_search_phrase = console.confirm_prompt.ask("Use search phrase")
        if use_search_phrase:
            custom_args["search_phrase"] = console.prompt.ask("Search phrase")

        # Sold out only / with stock only
        sold_out_only = console.confirm_prompt.ask("\nSold out only")
        if sold_out_only:
            custom_args["sold_out_only"] = True
            custom_args["with_stock_only"] = False
        else:
            custom_args["with_stock_only"] = console.confirm_prompt.ask(
                "\nWith stock only"
            )

        return custom_args

    def monitor(self, selected_item: ItemOverview | None = None) -> None:
        """
        Monitors an item. Asks the user to configure filters, then searches for
        favorite items matching the criteria and prompts the user to select one
        of them.
        If the selected item becomes available and checkout is enabled, the
        method initializes the checkout process.
        If the order fails and the item is no longer available, the monitoring
        process starts again.

        Args:
            selected_item (ItemOverview | None, optional): Item to monitor.
                                                           This option should
                                                           be used to restart
                                                           the monitor.
                                                           Defaults to None.

        Raises:
            SettingsError: If checkout is enabled but payment details are
                           missing. This check should always be false if the
                           config validation is working as expected.
        """
        # Fetch datadome cookie if no saved one exists, since endpoints like
        # the item or favorites endpoint are protected
        if not self._tgtg.session.cookies.get(name="datadome"):
            with console.loading(
                status=(
                    "Solving Datadome challenge. "
                    "This might take some seconds..."
                ),
            ):
                self._tgtg.fetch_datadome_cookie()
            console.clear()

        # Load values from config
        latitude = self._config.settings.account.latitude
        longitude = self._config.settings.account.longitude
        radius = self._config.settings.account.radius
        checkout_enabled = self._config.settings.application.enable_checkout
        delay = self._config.settings.monitor.delay_in_milliseconds
        start_time = self._config.settings.monitor.start_time
        end_time = self._config.settings.monitor.end_time
        use_time_frame = start_time is not None and end_time is not None

        # Start filter configuration and item selection if no item is provided
        # (meaning it is the first time running the method)
        if not selected_item:

            # Optional custom filters
            custom_filter = console.confirm_prompt.ask(
                "Customize search filter"
            )
            custom_args = {}
            if custom_filter:
                console.clear()
                custom_args = self._configure_filters()

            # Print notice to console and load favorites
            console.clear()
            with console.loading(
                status=(
                    "Loading your favorite items. "
                    "This might take some seconds..."
                ),
            ):
                items = self._get_items(
                    latitude=latitude,
                    longitude=longitude,
                    radius=radius,
                    favorites_only=True,
                    **custom_args,
                )
            console.clear()

            # Check if items were found
            if len(items) == 0:
                console.error("No favorites found.")
                console.info(
                    "Open the app on your phone and add favorites "
                    "to start monitoring.",
                    show_time=False,
                )
                return

            # Print result table to console
            table = Table(box=box.DOUBLE_EDGE, show_lines=True)
            table.add_column("#", justify="center")
            table.add_column("Name", justify="center")
            table.add_column("Price", justify="center")
            table.add_column("Sold Out", justify="center")
            for num, item in enumerate(items):
                row_data = [
                    str(num + 1),
                    item.name,
                    f"{item.currency_code} {item.price:.2f}",
                    "X" if item.items_available == 0 else "",
                ]
                table.add_row(*row_data)
            console.print(table)

            # Ask for item selection
            while True:
                selection = console.int_prompt.ask(
                    "\nSelect an item to monitor"
                )
                if not (
                    all(num in string.digits for num in str(selection))
                    and selection in range(1, len(items) + 1)
                ):
                    console.error(
                        "\nInvalid selection. "
                        "Please enter a number from the table above."
                    )
                    continue
                selected_item = items[selection - 1]
                break

        # Check for next_sales_window_purchase_start and ask user if the value
        # should be used to sleep until the start of the sales window
        item_details = self._get_item(
            latitude=latitude,
            longitude=longitude,
            item_id=selected_item.id,
        )
        next_sales_window_purchase_start = item_details.get(
            "next_sales_window_purchase_start"
        )
        sleep_until_start = False
        if next_sales_window_purchase_start:
            start_utc = datetime.fromisoformat(
                next_sales_window_purchase_start
            )
            start = start_utc.astimezone()
            console.clear()
            console.info(
                f"The next sales window opens at "
                f"{start:%Y-%m-%d %H:%M:%S %Z}.\n",
                show_time=False,
            )
            sleep_until_start = console.confirm_prompt.ask(
                "Do you want to sleep until then"
            )

            # Set start and end time (with one minute monitoring duration)
            if sleep_until_start:
                start_time = start
                end_time = start + timedelta(minutes=1)
                use_time_frame = True

        # Inner function to check if the current time is within the time frame
        def is_within_time_frame() -> bool:
            """
            Checks if the current time is within the time frame.

            Returns:
                bool: True if the current time is within the time frame,
                      otherwise False.
            """
            # No time frame used
            if not start_time or not end_time:
                return True

            # Automatic timeframe (using 'next_sales_window_purchase_start')
            if (
                isinstance(start_time, datetime)
                and isinstance(end_time, datetime)
            ):
                return start_time <= datetime.now().astimezone() <= end_time

            # Configured timeframe (using the settings)
            current_time = datetime.now().time()
            start = cast(time, start_time)  # only for type checking
            end = cast(time, end_time)      # only for type checking
            if start <= end:
                return start <= current_time <= end
            return start <= current_time or current_time <= end

        # Inner function for Rich's live display
        def get_monitoring_message(is_active: bool) -> str:
            """
            Provides the status message to be shown while monitoring an item.

            Args:
                is_active (bool): False if a monitoring time frame is used and
                                  the current time is outside of the active
                                  time frame, otherwise True.

            Returns:
                str: Status message to be shown in the console.
            """
            item = selected_item.name

            # Active time frame
            if is_active:
                current_time = datetime.now().astimezone()
                return (
                    f"Monitoring '{item}' to be back in stock.\n"
                    f"➤ Delay: {delay} ms\n"
                    f"➤ Last update: {current_time.strftime('%H:%M:%S %Z')}"
                )

            # Automatic start time
            if sleep_until_start:
                wake_up_time = cast(
                    datetime,
                    start_time,
                )

            # Configured start time
            else:
                current_time = datetime.now().astimezone()
                wake_up_time = datetime.combine(
                    date=current_time.date(),
                    time=cast(time, start_time),
                ).astimezone()

                # Add one day if current time is past the start time
                # Example: Start time is 21:00 and end time is 22:00.
                #          Current time is 23:00. Then the monitor
                #          needs to sleep until 21:00 of the next day.
                if wake_up_time <= current_time:
                    wake_up_time += timedelta(days=1)

            return (
                f"Sleeping until {wake_up_time:%Y-%m-%d %H:%M:%S %Z} before "
                f"starting to monitor '{item}'."
            )

        # Check time frame
        is_active = is_within_time_frame()

        # Loop until item is available
        console.clear()
        status_message = get_monitoring_message(is_active)
        with console.loading(status=status_message) as status:
            while True:
                # Check time if time frame is used
                if use_time_frame:
                    is_active = is_within_time_frame()

                # Check if item is available
                if is_active:
                    items_available = self._get_item(
                        latitude=latitude,
                        longitude=longitude,
                        item_id=selected_item.id,
                    )["items_available"]
                    if items_available > 0:
                        break

                # Update status message and sleep
                status.update(get_monitoring_message(is_active))
                if is_active:
                    sleep(delay / 1000)

                # Handle timeframes
                else:
                    current_time = datetime.now()

                    # Fetch the next sales window once the current one has
                    # passed
                    if (
                        sleep_until_start
                        and (
                            current_time.astimezone()
                            >= cast(datetime, start_time)
                        )
                    ):
                        item_details = self._get_item(
                            latitude=latitude,
                            longitude=longitude,
                            item_id=selected_item.id,
                        )
                        next_sales_window_purchase_start = item_details.get(
                            "next_sales_window_purchase_start"
                        )

                        # Check if there is a next sales window
                        if next_sales_window_purchase_start:
                            start_utc = datetime.fromisoformat(
                                next_sales_window_purchase_start
                            )
                            start = start_utc.astimezone()
                            start_time = start
                            end_time = (start + timedelta(minutes=1))

                            # Check to prevent negative sleep time
                            if start <= datetime.now().astimezone():
                                console.warning(
                                    "The next sales window has not moved on "
                                    "yet. Stopping...",
                                    show_time=False,
                                )
                                return
                        else:
                            console.warning(
                                "No next sales window found. Stopping...",
                                show_time=False,
                            )
                            return

                    # If using a configured timeframe, create datetime object
                    # with the current date
                    if isinstance(start_time, datetime):
                        start_dt = start_time
                        sleep_time = (
                            start_dt - current_time.astimezone()
                        ).total_seconds()

                    else:
                        start_dt = datetime.combine(
                            date=current_time.date(),
                            time=cast(time, start_time),
                        )

                        # Add one day if current time is past the start time
                        # Example: Start time is 21:00 and end time is 22:00.
                        #          Current time is 23:00. Then the monitor
                        #          needs to sleep until 21:00 of the next day.
                        if start_dt <= current_time:
                            start_dt += timedelta(days=1)

                        # Calculate sleep time
                        sleep_time = (start_dt - current_time).total_seconds()

                    # Sleep for the calculated time.
                    # Limited to 1 hour in case the 'next sales window' changes
                    # before the monitor awakes or in other rare cases like
                    # time changes (e.g. daylight saving time).
                    sleep(min(sleep_time, 3600))

        # Stop if checkout is disabled
        if not checkout_enabled:
            send_notification(
                topic=self._config.settings.monitor.ntfy_topic,
                title="Item available!",
                message=(
                    f"The monitored item '{selected_item.name}' is back in "
                    f"stock."
                ),
                headers={"tag": "bangbang"},
            )
            console.info("Checkout is disabled. Stopping...", show_time=False)
            return

        # Check for errors regarding payment setup
        # (should not happen if config validation is working as expected)
        if None in (
            self._config.settings.payment.card_number,
            self._config.settings.payment.card_expiry_month,
            self._config.settings.payment.card_expiry_year,
            self._config.settings.payment.card_security_code,
        ):
            raise SettingsError(
                "Invalid payment setup. "
                "Checkout is enabled but payment details are missing. "
            )

        # Start checkout
        # Not sending a notification until order is reserved to not slow down
        # the checkout process
        payment_service = OrderService(config=self._config, tgtg=self._tgtg)
        order_successful = False
        while not order_successful:
            console.clear()
            order_successful = payment_service.checkout_item(
                item_id=selected_item.id,
                item_name=selected_item.name,
            )
            if not order_successful:
                items_available = self._get_item(
                    latitude=latitude,
                    longitude=longitude,
                    item_id=selected_item.id,
                )["items_available"]
                if items_available < 1:
                    console.error(
                        "Item is no longer available. "
                        "Restarting monitoring...",
                        show_time=True,
                    )
                    return self.monitor(selected_item=selected_item)
                else:
                    console.info("Starting another checkout attempt...")
                    continue
        return
