import logging
from copy import deepcopy
from pathlib import Path

from lxml import etree as ET

logg = logging.getLogger(__name__)

FALLBACK_NS = "http://usawa.defalsify.org/"


def _get_local_name(element):
    """Extract local name from element tag (without namespace)"""
    tag = element.tag
    return tag.split("}")[-1] if "}" in tag else tag


def _find_child(parent, local_name):
    """Find child element by local name"""
    for child in parent:
        if _get_local_name(child) == local_name:
            return child
    return None


def _get_local_name(element):
    """Extract local name from element tag (without namespace)"""
    tag = element.tag
    return tag.split("}")[-1] if "}" in tag else tag


def _find_child(parent, local_name):
    """Find child element by local name, ignoring namespace."""
    for child in parent:
        if _get_local_name(child) == local_name:
            return child
    return None


def resolve_namespace(xml_tree) -> str:
    """Resolve the namespace URI from an XML tree.

    Tries nsmap first, then falls back to parsing the root tag,
    then falls back to the well-known usawa namespace.

    :param xml_tree: Root XML element.
    :type xml_tree: lxml.etree.Element
    :return: Namespace URI string.
    :rtype: str
    """
    ns_uri = xml_tree.nsmap.get(None)
    if ns_uri is not None:
        return ns_uri
    if "}" in xml_tree.tag:
        return xml_tree.tag.split("}")[0].strip("{")
    logg.warning("Could not resolve namespace, using fallback: %s", FALLBACK_NS)
    return FALLBACK_NS


def _find_entry_by_serial(xml_tree, ns_uri: str, serial: int):
    """Find an entry element by its serial number.

    :param xml_tree: Root XML element to search within.
    :type xml_tree: lxml.etree.Element
    :param ns_uri: Namespace URI.
    :type ns_uri: str
    :param serial: Entry serial number to find.
    :type serial: int
    :return: Matching entry element, or None if not found.
    :rtype: lxml.etree.Element or None
    """
    all_entries = xml_tree.findall(".//{%s}entry" % ns_uri)
    logg.debug("Searching %d entries for serial %d", len(all_entries), serial)

    for entry_elem in all_entries:
        data_elem = _find_child(entry_elem, "data")
        if data_elem is None:
            logg.warning("Entry without <data> element, skipping")
            continue

        serial_elem = _find_child(data_elem, "serial")
        if serial_elem is None:
            logg.warning("Entry without <serial> element, skipping")
            continue

        if int(serial_elem.text) == serial:
            logg.debug("Found target entry serial %d", serial)
            return entry_elem

    return None


def _build_incoming_element(ns_uri: str, target_entry, orig_incoming=None):
    """Build the <incoming> XML element from entry debit/credit values.

    :param ns_uri: Namespace URI.
    :type ns_uri: str
    :param target_entry: Entry element to read debit/credit amounts from.
    :type target_entry: lxml.etree.Element
    :param orig_incoming: Existing <incoming> element to copy digest/sig from.
    :type orig_incoming: lxml.etree.Element or None
    :return: Constructed <incoming> element.
    :rtype: lxml.etree.Element
    """
    data_elem = _find_child(target_entry, "data")

    debit_val = 0
    credit_val = 0

    if data_elem is not None:
        debit_elem = _find_child(data_elem, "debit")
        credit_elem = _find_child(data_elem, "credit")

        if debit_elem is not None:
            amount_elem = _find_child(debit_elem, "amount")
            if amount_elem is not None:
                debit_val = int(amount_elem.text)

        if credit_elem is not None:
            amount_elem = _find_child(credit_elem, "amount")
            if amount_elem is not None:
                credit_val = int(amount_elem.text)

    expense = -abs(debit_val)
    asset = credit_val

    incoming = ET.Element("{%s}incoming" % ns_uri)
    incoming.set("serial", "0")

    real = ET.SubElement(incoming, "{%s}real" % ns_uri)
    real.set("unit", "BTC")

    ET.SubElement(real, "{%s}income" % ns_uri).text = "0"
    ET.SubElement(real, "{%s}expense" % ns_uri).text = str(expense)
    ET.SubElement(real, "{%s}asset" % ns_uri).text = str(asset)
    ET.SubElement(real, "{%s}liability" % ns_uri).text = "0"

    if orig_incoming is not None:
        for tag in ["digest", "sig"]:
            elem = _find_child(orig_incoming, tag)
            if elem is not None:
                incoming.append(deepcopy(elem))

    return incoming


def _build_export_root(xml_tree, ns_uri: str, target_entry, incoming):
    """Assemble the export root element with header metadata, incoming, and target entry.

    :param xml_tree: Source ledger XML tree to copy header elements from.
    :type xml_tree: lxml.etree.Element
    :param ns_uri: Namespace URI.
    :type ns_uri: str
    :param target_entry: The entry element to include in the export.
    :type target_entry: lxml.etree.Element
    :param incoming: The <incoming> element to include.
    :type incoming: lxml.etree.Element
    :return: Assembled root element.
    :rtype: lxml.etree.Element
    """
    root = ET.Element("{%s}ledger" % ns_uri, nsmap={None: ns_uri})
    root.set("version", xml_tree.get("version", ""))

    for tag in ["topic", "generated", "src", "units", "identity"]:
        elem = _find_child(xml_tree, tag)
        if elem is not None:
            logg.debug("Copying header element: %s", tag)
            root.append(deepcopy(elem))

    root.append(incoming)
    root.append(deepcopy(target_entry))

    final_entries = root.findall(".//{%s}entry" % ns_uri)
    logg.debug("Export root contains %d entry(ies)", len(final_entries))

    return root


def _write_xml_to_file(root, output_path: str) -> None:
    """Serialize an XML element tree and write it to a file.

    Creates parent directories if they do not exist.

    :param root: Root XML element to serialize.
    :type root: lxml.etree.Element
    :param output_path: Destination file path.
    :type output_path: str
    :raises PermissionError: If the file cannot be written.
    :raises IOError: If a file system error occurs.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    xml_string = ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    )

    with open(output_file, "wb") as f:
        f.write(xml_string)

    logg.debug("Wrote XML to %s (%d bytes)", output_path, len(xml_string))
