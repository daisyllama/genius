import re
import string


def clean_lyrics(text: str) -> str:
    """
    Clean lyrics for analysis:
    - remove bracketed tags like [Chorus], [Verse], [Bridge]
    - convert text to lowercase
    - remove punctuation
    - keep stopwords and pronouns (no stopword removal)
    - collapse repeated whitespace

    Returns:
        Cleaned lyrics as a string.
    """
    if text is None:
        return ""

    text = str(text)
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text
