"""A curated set of common technical/professional skills and text helpers.

Used to surface concrete, recognizable skill gaps in addition to the generic
keyword analysis. Not exhaustive — it is a signal, not a source of truth.
"""

from __future__ import annotations

import re

# Canonical skill -> set of aliases (all lowercase). Matching is done on
# word boundaries so "r" won't match "react".
SKILL_ALIASES: dict[str, set[str]] = {
    "python": {"python"},
    "java": {"java"},
    "javascript": {"javascript", "js"},
    "typescript": {"typescript", "ts"},
    "c++": {"c++", "cpp"},
    "c#": {"c#", "csharp"},
    "go": {"go", "golang"},
    "rust": {"rust"},
    "sql": {"sql"},
    "nosql": {"nosql"},
    "react": {"react", "react.js", "reactjs"},
    "angular": {"angular", "angularjs"},
    "vue": {"vue", "vue.js", "vuejs"},
    "node.js": {"node", "node.js", "nodejs"},
    "django": {"django"},
    "flask": {"flask"},
    "fastapi": {"fastapi"},
    "spring": {"spring", "spring boot", "springboot"},
    "aws": {"aws", "amazon web services"},
    "azure": {"azure"},
    "gcp": {"gcp", "google cloud"},
    "docker": {"docker"},
    "kubernetes": {"kubernetes", "k8s"},
    "terraform": {"terraform"},
    "ansible": {"ansible"},
    "jenkins": {"jenkins"},
    "ci/cd": {"ci/cd", "cicd", "ci cd"},
    "git": {"git"},
    "linux": {"linux", "unix"},
    "postgresql": {"postgresql", "postgres"},
    "mysql": {"mysql"},
    "mongodb": {"mongodb", "mongo"},
    "redis": {"redis"},
    "kafka": {"kafka"},
    "spark": {"spark", "apache spark"},
    "hadoop": {"hadoop"},
    "pandas": {"pandas"},
    "numpy": {"numpy"},
    "scikit-learn": {"scikit-learn", "sklearn", "scikit learn"},
    "tensorflow": {"tensorflow"},
    "pytorch": {"pytorch"},
    "machine learning": {"machine learning", "ml"},
    "deep learning": {"deep learning"},
    "nlp": {"nlp", "natural language processing"},
    "data analysis": {"data analysis", "data analytics"},
    "tableau": {"tableau"},
    "power bi": {"power bi", "powerbi"},
    "excel": {"excel"},
    "rest": {"rest", "rest api", "restful"},
    "graphql": {"graphql"},
    "microservices": {"microservices", "microservice"},
    "agile": {"agile", "scrum"},
    "project management": {"project management"},
    "html": {"html", "html5"},
    "css": {"css", "css3"},
    # Languages
    ".net": {".net", "dotnet", "asp.net"},
    "scala": {"scala"},
    "kotlin": {"kotlin"},
    "ruby": {"ruby", "ruby on rails", "rails"},
    "php": {"php"},
    "swift": {"swift"},
    "r": {"r programming", "rlang", "rstudio"},  # avoid bare "r" (too many false positives)
    "matlab": {"matlab"},
    "perl": {"perl"},
    "bash": {"bash", "shell scripting"},
    "powershell": {"powershell"},
    # Databases / stores
    "elasticsearch": {"elasticsearch", "elastic search", "elk"},
    "dynamodb": {"dynamodb", "dynamo db"},
    "cassandra": {"cassandra"},
    "oracle": {"oracle"},
    "sqlite": {"sqlite"},
    "snowflake": {"snowflake"},
    # Data engineering / ML
    "airflow": {"airflow", "apache airflow"},
    "databricks": {"databricks"},
    "etl": {"etl"},
    "keras": {"keras"},
    "xgboost": {"xgboost"},
    "opencv": {"opencv"},
    # Messaging / APIs
    "rabbitmq": {"rabbitmq", "rabbit mq"},
    "grpc": {"grpc"},
    # Testing
    "selenium": {"selenium"},
    "pytest": {"pytest"},
    "cypress": {"cypress"},
    "jest": {"jest"},
    "junit": {"junit"},
    # Frontend
    "next.js": {"next.js", "nextjs"},
    "redux": {"redux"},
    "tailwind": {"tailwind", "tailwind css"},
    "bootstrap": {"bootstrap"},
    "jquery": {"jquery"},
    "sass": {"sass", "scss"},
    "webpack": {"webpack"},
    # Mobile
    "android": {"android"},
    "ios": {"ios"},
    "react native": {"react native"},
    "flutter": {"flutter"},
    # Tooling
    "jira": {"jira"},
    "confluence": {"confluence"},
}


def _alias_pattern(alias: str) -> re.Pattern[str]:
    # Escape regex specials (c++, c#, ci/cd, node.js) then require boundaries
    # that are not other word chars, so aliases embedded in longer words don't match.
    #
    # The left boundary also excludes a leading '.', so a file-extension suffix
    # like ".js" / ".ts" in "react.js" or "node.ts" does NOT trip the short "js"
    # / "ts" aliases. The right boundary stays permissive of '.', so "react.js"
    # still matches the "react" alias.
    escaped = re.escape(alias)
    return re.compile(rf"(?<![\w+#.]){escaped}(?![\w+#])", re.IGNORECASE)


_COMPILED = {
    skill: [_alias_pattern(a) for a in aliases]
    for skill, aliases in SKILL_ALIASES.items()
}


def find_skills(text: str) -> set[str]:
    """Return the set of canonical skills detected in ``text``."""
    found = set()
    for skill, patterns in _COMPILED.items():
        if any(p.search(text) for p in patterns):
            found.add(skill)
    return found
