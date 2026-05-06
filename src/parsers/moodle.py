"""
Parser: Résumé Moodle IDU.html
Extracts course information from the Moodle search results page.
"""

from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


def parse_moodle(path: Path) -> list[dict]:
    """
    Parse the Moodle summary HTML file.

    Extracts course boxes with: title, category, teachers, description, link.

    Returns:
        List of dicts with keys:
            titre, categorie, professeurs (list), description, lien
    """
    if BeautifulSoup is None:
        return []

    with open(path, encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    course_boxes = soup.find_all("div", class_="coursebox")

    courses = []
    for box in course_boxes:
        # Title and link
        title_tag = box.find("h3", class_="coursename")
        link_tag = title_tag.find("a") if title_tag else None
        title = link_tag.text.strip() if link_tag else "Titre inconnu"
        link = link_tag["href"] if link_tag and link_tag.has_attr("href") else ""

        # Category
        cat_tag = box.find("div", class_="coursecat")
        cat_link = cat_tag.find("a") if cat_tag else None
        category = cat_link.text.strip() if cat_link else "Non catégorisé"

        # Teachers
        teachers_list = []
        teachers_tag = box.find("ul", class_="teachers")
        if teachers_tag:
            for li in teachers_tag.find_all("li"):
                a_tag = li.find("a")
                if a_tag:
                    teachers_list.append(a_tag.text.strip())

        # Description / summary
        summary_tag = box.find("div", class_="summary")
        description = summary_tag.text.strip() if summary_tag else ""
        description = " ".join(description.split())  # normalize whitespace

        courses.append({
            "titre": title,
            "categorie": category,
            "professeurs": teachers_list,
            "description": description,
            "lien": link,
        })

    return courses
