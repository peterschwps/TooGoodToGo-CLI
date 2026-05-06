import string
from datetime import datetime
from time import sleep
from typing import Any, cast, get_args

from rich import box
from rich.table import Table

from tgtg_cli import config, tgtg
from tgtg_cli.cli import console
from tgtg_cli.cli.menu import show_selection
from tgtg_cli.cli.types import DietCategory, ItemCategory, SortOption
from tgtg_cli.services.order_service import OrderService
from tgtg_cli.utils.exceptions import SettingsError
from tgtg_cli.utils.models import ItemOverview
from tgtg_cli.utils.notifications import send_notification


class ProductService:
    """
    Grouping of all product-related functions.
    """

    @staticmethod
    def _get_item_availability(
        latitude: float,
        longitude: float,
        item_id: str,
    ) -> int:
        """
        Retrieves the current stock count for a specific item.

        Args:
            latitude (float): Latitude used as search origin.
            longitude (float): Longitude used as search origin.
            item_id (str): ID of the item to look up.

        Returns:
            int: Number of currently available items.
        """
        item = tgtg.get_item(
            latitude=latitude,
            longitude=longitude,
            item_id=item_id,
        )
        return item["items_available"]

    @staticmethod
    def _get_items(
        latitude: float,
        longitude: float,
        radius: int,
        favorites_only: bool = False,
        item_categories: list[ItemCategory] | None = None,
        diet_categories: list[DietCategory] | None = None,
        search_phrase: str | None = None,
        sold_out_only: bool = False,
        with_stock_only: bool = False,
        hidden_only: bool = False,
        sort_option: SortOption = "RELEVANCE",
    ) -> list[ItemOverview]:
        """
        Retrieves all items within a given radius from a given location. Allows
        configuration of various filters and sorting options.
        Iterates over all result pages and combines the items from each page.

        Args:
            latitude (float): Latitude used as search origin.
            longitude (float): Longitude used as search origin.
            radius (int): Search radius in kilometers.
            favorites_only (bool, optional): If only favorites should be
                                             returned.
                                             Defaults to False.
            item_categories (list[ItemCategory] | None, optional): Specific
                                                                   item
                                                                   categories
                                                                   to filter
                                                                   for.
                                                                   Defaults to
                                                                   None.
            diet_categories (list[DietCategory] | None, optional): Specific
                                                                   diet
                                                                   categories
                                                                   to filter
                                                                   for.
                                                                   Defaults to
                                                                   None.
            search_phrase (str | None, optional): Search query to use.
                                                  Defaults to None.
            sold_out_only (bool, optional): If only sold-out items should be
                                            returned. This can be helpful when
                                            starting the monitoring process.
                                            Defaults to False.
            with_stock_only (bool, optional): If only in-stock items should be
                                              returned.
                                              Defaults to False.
            hidden_only (bool, optional): If only hidden items should be
                                          returned.
                                          Defaults to False.
            sort_option (SortOption, optional): Sort mode for the results.
                                                Defaults to "RELEVANCE".

        Returns:
            list[ItemOverview]: List of all items matching the criteria.
        """
        # IMPORTANT: keep page_size=20, changing it can lead to missing items
        #            or duplicates!
        all_items: list[ItemOverview] = []
        search_args = {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
            "page_size": 20,  # see note above!
            "page": 1,
            "favorites_only": favorites_only,
            "item_categories": item_categories,
            "diet_categories": diet_categories,
            "search_phrase": search_phrase,
            "with_stock_only": with_stock_only,
            "hidden_only": hidden_only,
            "sort_option": sort_option,
            "expand_radius_if_not_enough_items": False,
        }
        search_result = tgtg.get_items(**search_args)

        # Combine items (if expanded radius is used items list is empty
        # and vice versa))
        items = search_result["items"] + search_result["items_expanded_radius"]

        # Iterate over all result pages
        while len(items) != 0:
            for item in items:
                # Skip available items if filter_only_sold_out is True
                if sold_out_only and item["items_available"] != 0:
                    continue

                # Create item overview
                price_minor_units = item["item"]["item_price"]["minor_units"]
                decimals = item["item"]["item_price"]["decimals"]
                item_overview = ItemOverview(
                    id=item["item"]["item_id"],
                    name=item["display_name"],
                    price=round(price_minor_units / 10**decimals, 2),
                    currency_code=item["item"]["item_price"]["code"],
                    items_available=item["items_available"],
                )
                all_items.append(item_overview)

            # Fetch next page
            search_args["page"] += 1
            sleep(1)  # to prevent rate limiting
            search_result = tgtg.get_items(**search_args)

            # Update items with contents of new page
            items = (
                search_result["items"] + search_result["items_expanded_radius"]
            )

        return all_items

    @staticmethod
    def _configure_filters() -> dict[str, Any]:
        """
        Configures all filter options.

        Returns:
            dict[str, Any]: All selected filter options.
        """
        custom_args = {}

        # Favorites only
        custom_args["favorites_only"] = console.confirm_prompt.ask(
            "Favorites only"
        )

        # Item categories
        configure_item_categories = console.confirm_prompt.ask(
            "\nConfigure item categories"
        )
        if configure_item_categories:
            categories_available = get_args(ItemCategory)
            selections = show_selection(
                options=categories_available, multi_selection=True
            )
            custom_args["item_categories"] = [
                categories_available[category]
                for category in cast(list[int], selections)
            ]

        # Diet categories
        configure_diet_categories = console.confirm_prompt.ask(
            "\nConfigure diet categories"
        )
        if configure_diet_categories:
            categories_available = get_args(DietCategory)
            selections = show_selection(
                options=categories_available,
                multi_selection=True,
            )
            custom_args["diet_categories"] = [
                categories_available[category]
                for category in cast(list[int], selections)
            ]

        # Search phrase
        use_search_phrase = console.confirm_prompt.ask(
            "\nUse search phrase"
        )
        if use_search_phrase:
            custom_args["search_phrase"] = console.prompt.ask(
                "Search phrase"
            )

        # Sold out only / with stock only
        sold_out_only = console.confirm_prompt.ask("\nSold out only")
        if sold_out_only:
            custom_args["sold_out_only"] = True
            custom_args["with_stock_only"] = False
        else:
            custom_args["with_stock_only"] = console.confirm_prompt.ask(
                "\nWith stock only"
            )

        # Hidden only
        custom_args["hidden_only"] = console.confirm_prompt.ask(
            "\nHidden only"
        )

        # Sort option
        configure_sort_option = console.confirm_prompt.ask(
            "\nConfigure sort option"
        )
        if configure_sort_option:
            sort_options_available = get_args(SortOption)
            selection = show_selection(sort_options_available)
            selection = cast(int, selection)
            custom_args["sort_option"] = sort_options_available[selection]
        else:
            custom_args["sort_option"] = "RELEVANCE"

        return custom_args

    @staticmethod
    def monitor(selected_item: ItemOverview | None = None) -> None:
        """
        Monitors an item. Asks the user to configure filters, then searches for
        items matching the criteria and prompts the user to select one of them.
        If the selected item is becomes available and checkout is enabled, the
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
        # Load values from config
        latitude = config.settings.account.latitude
        longitude = config.settings.account.longitude
        radius = config.settings.account.radius
        
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
                custom_args = ProductService._configure_filters()

            # Print notice to console
            console.clear()
            with console.loading(
                status=(
                    "Searching for items in your area. "
                    "This might take some seconds..."
                ),
            ):
                items = ProductService._get_items(
                    latitude=latitude,
                    longitude=longitude,
                    radius=radius,
                    **custom_args,
                )
            console.clear()

            # Check if items were found
            if len(items) == 0:
                console.error("No items found in your area.")
                console.info(
                    "Please try a different area, increase the radius "
                    "or change the filter settings.",
                    show_time=False,
                )
                console.info(
                    "Keep in mind that you need to restart the program "
                    "if you change your settings.",
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

        # Inner function for Rich's live display
        def get_monitoring_message() -> str:
            """
            Provides the status message to be shown while monitoring an item.

            Returns:
                str: Status message to be shown in the console.
            """
            item = selected_item.name
            delay = config.settings.monitor.delay_in_milliseconds
            return (
                f"Monitoring '{item}' to be back in stock...\n"
                f"➤ Delay: {delay} ms\n"
                f"➤ Last update: {datetime.now().strftime('%H:%M:%S')}"
            )

        # Loop until item is available
        console.clear()
        with console.loading(status=get_monitoring_message()) as status:
            while True:
                items_available = ProductService._get_item_availability(
                    latitude=latitude,
                    longitude=longitude,
                    item_id=selected_item.id,
                )
                if items_available > 0:
                    break
                status.update(get_monitoring_message())
                sleep(config.settings.monitor.delay_in_milliseconds / 1000)

        # Stop if checkout is disabled
        if not config.settings.application.enable_checkout:
            send_notification(
                topic=config.settings.monitor.ntfy_topic,
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
            config.settings.payment.card_number,
            config.settings.payment.card_expiry_month,
            config.settings.payment.card_expiry_year,
            config.settings.payment.card_security_code,
        ):
            raise SettingsError(
                "Invalid payment setup. "
                "Checkout is enabled but payment details are missing. "
            )

        # Start checkout
        # Not sending a notification until order is reserved to not slow down
        # the checkout process
        payment_service = OrderService()
        order_successful = False
        while not order_successful:
            console.clear()
            order_successful = payment_service.checkout_item(
                item_id=selected_item.id,
                item_name=selected_item.name,
            )
            if not order_successful:
                items_available = ProductService._get_item_availability(
                    latitude=latitude,
                    longitude=longitude,
                    item_id=selected_item.id,
                )
                if items_available < 1:
                    console.error(
                        "Item is no longer available. "
                        "Restarting monitoring...",
                        show_time=True,
                    )
                    return ProductService.monitor(selected_item=selected_item)
                else:
                    console.info("Starting another checkout attempt...")
                    continue
        return
