from dependency_injector import containers, providers

from tgtg_cli.apis.tgtg import TGTG
from tgtg_cli.cli.config import Config
from tgtg_cli.services.account_service import AccountService
from tgtg_cli.services.order_service import OrderService
from tgtg_cli.services.product_service import ProductService


class Container(containers.DeclarativeContainer):
    """
    Defines providers for the application's components. All providers are lazy!
    Singletons are cached after the first call. Factories build a new instance
    on each call.
    """
    # ========== SINGLETONS ==========
    config = providers.Singleton(Config)

    tgtg = providers.Singleton(
        TGTG,
        config=config,
    )

    account_service = providers.Singleton(
        AccountService,
        config=config,
        tgtg=tgtg,
    )

    product_service = providers.Singleton(
        ProductService,
        config=config,
        tgtg=tgtg,
    )

    # ========== FACTORIES ===========
    order_service = providers.Factory(
        OrderService,
        config=config,
        tgtg=tgtg,
    )
