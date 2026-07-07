"""Collectible market connector foundation."""

from onecool_os.connectors.collectibles.base import BaseCollectibleConnector
from onecool_os.connectors.collectibles.cardladder import (
    CardLadderConnector,
)
from onecool_os.connectors.collectibles.card_ladder_import import (
    CardLadderImportError,
)
from onecool_os.connectors.collectibles.card_ladder_import import (
    CardLadderImportResult,
)
from onecool_os.connectors.collectibles.card_ladder_import import (
    CardLadderImportSummary,
)
from onecool_os.connectors.collectibles.card_ladder_import import (
    CardLadderManualImporter,
)
from onecool_os.connectors.collectibles.ebay import EbaySoldConnector
from onecool_os.connectors.collectibles.ebay_import import (
    EbaySoldImportError,
)
from onecool_os.connectors.collectibles.ebay_import import (
    EbaySoldImportResult,
)
from onecool_os.connectors.collectibles.ebay_import import (
    EbaySoldManualImporter,
)
from onecool_os.connectors.collectibles.enums import CollectibleMarketSource
from onecool_os.connectors.collectibles.enums import CollectibleSourceRole
from onecool_os.connectors.collectibles.enums import source_role_for_source
from onecool_os.connectors.collectibles.fanatics import FanaticsConnector
from onecool_os.connectors.collectibles.goldin import GoldinConnector
from onecool_os.connectors.collectibles.models import (
    CollectibleConnectorError,
)
from onecool_os.connectors.collectibles.models import CollectibleMarketRecord
from onecool_os.connectors.collectibles.normalization import (
    normalize_collectible_market_record,
)
from onecool_os.connectors.collectibles.psa_import import ImportSummary
from onecool_os.connectors.collectibles.psa_import import PSACollectionImporter
from onecool_os.connectors.collectibles.psa_import import PSAImportError
from onecool_os.connectors.collectibles.psa_import import PSAImportResult
from onecool_os.connectors.collectibles.pwcc import PWCCConnector

__all__ = [
    "BaseCollectibleConnector",
    "CardLadderConnector",
    "CardLadderImportError",
    "CardLadderImportResult",
    "CardLadderImportSummary",
    "CardLadderManualImporter",
    "CollectibleConnectorError",
    "CollectibleMarketRecord",
    "CollectibleMarketSource",
    "CollectibleSourceRole",
    "EbaySoldConnector",
    "EbaySoldImportError",
    "EbaySoldImportResult",
    "EbaySoldManualImporter",
    "FanaticsConnector",
    "GoldinConnector",
    "ImportSummary",
    "PSACollectionImporter",
    "PSAImportError",
    "PSAImportResult",
    "PWCCConnector",
    "normalize_collectible_market_record",
    "source_role_for_source",
]
