import logging
from pathlib import Path

from lxml import etree as ET

logg = logging.getLogger("usawa.xml_utils")


def _write_xml_to_file(xml_string, output_path: str) -> None:

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "wb") as f:
        if isinstance(xml_string, str):
            xml_string = xml_string.encode("utf-8")
        f.write(xml_string)

    logg.debug("Wrote XML to %s (%d bytes)", output_path, len(xml_string))
