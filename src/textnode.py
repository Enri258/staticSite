import re
from enum import Enum
from htmlnode import LeafNode, ParentNode


class TextType(Enum):
    TEXT = "text"
    BOLD = "bold"
    ITALIC = "italic"
    CODE = "code"
    LINK = "link"
    IMAGE = "image"


class TextNode:
    def __init__(self, text, text_type, url=None):
        self.text = text
        self.text_type = text_type
        self.url = url

    def __eq__(self, other):
        return (
            self.text == other.text
            and self.text_type == other.text_type
            and self.url == other.url
        )

    def __repr__(self):
        return f"TextNode({self.text}, {self.text_type.value}, {self.url})"


def text_node_to_html_node(text_node):
    if text_node.text_type == TextType.TEXT:
        return LeafNode(None, text_node.text)
    if text_node.text_type == TextType.BOLD:
        return LeafNode("b", text_node.text)
    if text_node.text_type == TextType.ITALIC:
        return LeafNode("i", text_node.text)
    if text_node.text_type == TextType.CODE:
        return LeafNode("code", text_node.text)
    if text_node.text_type == TextType.LINK:
        return LeafNode("a", text_node.text, {"href": text_node.url})
    if text_node.text_type == TextType.IMAGE:
        return LeafNode("img", "", {"src": text_node.url, "alt": text_node.text})

    raise Exception("invalid text type")


def split_nodes_delimiter(old_nodes, delimiter, text_type):
    new_nodes = []

    for old_node in old_nodes:
        if old_node.text_type != TextType.TEXT:
            new_nodes.append(old_node)
            continue

        split_text = old_node.text.split(delimiter)

        if len(split_text) % 2 == 0:
            raise Exception("invalid markdown, formatted section not closed")

        for i in range(len(split_text)):
            if split_text[i] == "":
                continue

            if i % 2 == 0:
                new_nodes.append(TextNode(split_text[i], TextType.TEXT))
            else:
                new_nodes.append(TextNode(split_text[i], text_type))

    return new_nodes

def extract_markdown_images(text):
    return re.findall(r"!\[([^\[\]]*)\]\(([^\(\)]*)\)", text)


def extract_markdown_links(text):
    return re.findall(r"(?<!!)\[([^\[\]]*)\]\(([^\(\)]*)\)", text)

def split_nodes_image(old_nodes):
    new_nodes = []

    for old_node in old_nodes:
        if old_node.text_type != TextType.TEXT:
            new_nodes.append(old_node)
            continue

        original_text = old_node.text
        images = extract_markdown_images(original_text)

        if len(images) == 0:
            new_nodes.append(old_node)
            continue

        for image_alt, image_link in images:
            sections = original_text.split(f"![{image_alt}]({image_link})", 1)

            if len(sections) != 2:
                raise ValueError("invalid markdown, image section not found")

            if sections[0] != "":
                new_nodes.append(TextNode(sections[0], TextType.TEXT))

            new_nodes.append(TextNode(image_alt, TextType.IMAGE, image_link))
            original_text = sections[1]

        if original_text != "":
            new_nodes.append(TextNode(original_text, TextType.TEXT))

    return new_nodes


def split_nodes_link(old_nodes):
    new_nodes = []

    for old_node in old_nodes:
        if old_node.text_type != TextType.TEXT:
            new_nodes.append(old_node)
            continue

        original_text = old_node.text
        links = extract_markdown_links(original_text)

        if len(links) == 0:
            new_nodes.append(old_node)
            continue

        for link_text, link_url in links:
            sections = original_text.split(f"[{link_text}]({link_url})", 1)

            if len(sections) != 2:
                raise ValueError("invalid markdown, link section not found")

            if sections[0] != "":
                new_nodes.append(TextNode(sections[0], TextType.TEXT))

            new_nodes.append(TextNode(link_text, TextType.LINK, link_url))
            original_text = sections[1]

        if original_text != "":
            new_nodes.append(TextNode(original_text, TextType.TEXT))

    return new_nodes

def text_to_textnodes(text):
    nodes = [TextNode(text, TextType.TEXT)]
    nodes = split_nodes_image(nodes)
    nodes = split_nodes_link(nodes)
    nodes = split_nodes_delimiter(nodes, "**", TextType.BOLD)
    nodes = split_nodes_delimiter(nodes, "_", TextType.ITALIC)
    nodes = split_nodes_delimiter(nodes, "`", TextType.CODE)
    return nodes

def markdown_to_blocks(markdown):
    blocks = markdown.split("\n\n")
    filtered_blocks = []

    for block in blocks:
        stripped_block = block.strip()
        if stripped_block != "":
            filtered_blocks.append(stripped_block)

    return filtered_blocks

class BlockType(Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    CODE = "code"
    QUOTE = "quote"
    UNORDERED_LIST = "unordered_list"
    ORDERED_LIST = "ordered_list"


def block_to_block_type(block):
    lines = block.split("\n")

    if block.startswith("#"):
        parts = block.split(" ", 1)
        if len(parts) > 1:
            hashes = parts[0]
            if 1 <= len(hashes) <= 6 and all(char == "#" for char in hashes):
                return BlockType.HEADING

    if block.startswith("```") and block.endswith("```"):
        return BlockType.CODE

    if all(line.startswith(">") for line in lines):
        return BlockType.QUOTE

    if all(line.startswith("- ") for line in lines):
        return BlockType.UNORDERED_LIST

    is_ordered_list = True
    for i, line in enumerate(lines, start=1):
        if not line.startswith(f"{i}. "):
            is_ordered_list = False
            break

    if is_ordered_list:
        return BlockType.ORDERED_LIST

    return BlockType.PARAGRAPH

def text_to_children(text):
    text_nodes = text_to_textnodes(text)
    children = []

    for text_node in text_nodes:
        children.append(text_node_to_html_node(text_node))

    return children


def markdown_to_html_node(markdown):
    blocks = markdown_to_blocks(markdown)
    children = []

    for block in blocks:
        block_type = block_to_block_type(block)

        if block_type == BlockType.PARAGRAPH:
            paragraph = block.replace("\n", " ")
            children.append(ParentNode("p", text_to_children(paragraph)))

        elif block_type == BlockType.HEADING:
            level = 0
            for char in block:
                if char == "#":
                    level += 1
                else:
                    break
            text = block[level + 1:]
            children.append(ParentNode(f"h{level}", text_to_children(text)))

        elif block_type == BlockType.CODE:
            text = block[4:-3]
            text_node = TextNode(text, TextType.TEXT)
            code_node = text_node_to_html_node(text_node)
            children.append(ParentNode("pre", [ParentNode("code", [code_node])]))

        elif block_type == BlockType.QUOTE:
            lines = block.split("\n")
            cleaned_lines = []
            for line in lines:
                if line.startswith("> "):
                    cleaned_lines.append(line[2:])
                else:
                    cleaned_lines.append(line[1:])
            quote_text = " ".join(cleaned_lines)
            children.append(ParentNode("blockquote", text_to_children(quote_text)))

        elif block_type == BlockType.UNORDERED_LIST:
            lines = block.split("\n")
            list_items = []
            for line in lines:
                text = line[2:]
                list_items.append(ParentNode("li", text_to_children(text)))
            children.append(ParentNode("ul", list_items))

        elif block_type == BlockType.ORDERED_LIST:
            lines = block.split("\n")
            list_items = []
            for line in lines:
                text = line.split(". ", 1)[1]
                list_items.append(ParentNode("li", text_to_children(text)))
            children.append(ParentNode("ol", list_items))

    return ParentNode("div", children)

