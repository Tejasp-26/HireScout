"""Skill vocabulary with aliases, used to normalise and detect skills.

Canonical name -> aliases (matched case-insensitively on word boundaries).
The canonical name itself is always an alias too.
"""

import re

SKILLS: dict[str, list[str]] = {
    # Languages
    "Python": [],
    "Java": [],
    "JavaScript": ["javascript", "ecmascript"],
    "TypeScript": [],
    "C++": ["cpp"],
    "C#": ["c sharp", "csharp"],
    "Go": ["golang"],
    "Rust": [],
    "Kotlin": [],
    "Swift": [],
    "Ruby": [],
    "PHP": [],
    "Scala": [],
    "R": [],
    "MATLAB": [],
    "SQL": [],
    "Bash": ["shell scripting", "shell script"],
    "Dart": [],
    # Frontend
    "React": ["react.js", "reactjs"],
    "Next.js": ["nextjs", "next js"],
    "Angular": ["angularjs", "angular.js"],
    "Vue.js": ["vue", "vuejs"],
    "Redux": [],
    "HTML": ["html5"],
    "CSS": ["css3"],
    "Tailwind CSS": ["tailwind", "tailwindcss"],
    "Bootstrap": [],
    "Figma": [],
    # Backend
    "Node.js": ["node", "nodejs", "node js"],
    "Express": ["express.js", "expressjs"],
    "Django": [],
    "Flask": [],
    "FastAPI": [],
    "Spring Boot": ["spring", "springboot"],
    "ASP.NET": [".net", "dotnet", "asp.net core"],
    "Ruby on Rails": ["rails"],
    "GraphQL": [],
    "REST APIs": ["rest api", "restful", "rest apis", "restful apis"],
    "gRPC": [],
    "Microservices": ["microservice"],
    # Mobile
    "React Native": [],
    "Flutter": [],
    "Android": [],
    "iOS": [],
    # Data stores
    "PostgreSQL": ["postgres", "postgresql"],
    "MySQL": [],
    "MongoDB": ["mongo"],
    "Redis": [],
    "SQLite": [],
    "Oracle": [],
    "Elasticsearch": ["elastic search"],
    "Cassandra": [],
    "DynamoDB": [],
    "Snowflake": [],
    "BigQuery": [],
    # Cloud & DevOps
    "AWS": ["amazon web services"],
    "Azure": ["microsoft azure"],
    "GCP": ["google cloud", "google cloud platform"],
    "Docker": [],
    "Kubernetes": ["k8s"],
    "Terraform": [],
    "Ansible": [],
    "Jenkins": [],
    "GitHub Actions": [],
    "CI/CD": ["ci cd", "continuous integration"],
    "Linux": [],
    "Git": [],
    "Nginx": [],
    "Serverless": ["aws lambda", "lambda"],
    # Data & ML
    "Machine Learning": ["ml"],
    "Deep Learning": [],
    "NLP": ["natural language processing"],
    "Computer Vision": [],
    "Generative AI": ["genai", "gen ai"],
    "LLMs": ["llm", "large language models", "large language model"],
    "RAG": ["retrieval augmented generation", "retrieval-augmented generation"],
    "LangChain": [],
    "TensorFlow": [],
    "PyTorch": [],
    "Keras": [],
    "scikit-learn": ["sklearn", "scikit learn"],
    "Pandas": [],
    "NumPy": [],
    "Matplotlib": [],
    "Seaborn": [],
    "Data Analysis": ["data analytics"],
    "Data Science": [],
    "Data Engineering": [],
    "Statistics": [],
    "Apache Spark": ["spark", "pyspark"],
    "Hadoop": [],
    "Kafka": ["apache kafka"],
    "Airflow": ["apache airflow"],
    "ETL": [],
    "Power BI": ["powerbi"],
    "Tableau": [],
    "Excel": ["ms excel", "microsoft excel"],
    "FAISS": [],
    "Hugging Face": ["huggingface", "transformers"],
    "OpenCV": [],
    # Testing & practices
    "Unit Testing": ["unit tests"],
    "Pytest": [],
    "Jest": [],
    "Selenium": [],
    "Cypress": [],
    "Agile": ["scrum"],
    "System Design": [],
    "Data Structures": ["dsa", "data structures and algorithms"],
    # Security
    "Cybersecurity": ["cyber security", "information security"],
    "OAuth": ["oauth2", "oauth 2.0"],
    "JWT": [],
    # Business / non-engineering
    "Project Management": [],
    "Product Management": [],
    "Salesforce": [],
    "SAP": [],
    "ServiceNow": [],
    "Jira": [],
    "Communication": [],
    "Leadership": [],
    "Recruitment": ["recruiting", "talent acquisition"],
}

# Canonical names that are ordinary English words or single letters when
# lower-cased; only match them in their exact canonical casing.
_CASE_SENSITIVE = {"Go", "R", "Swift", "Rust", "Express", "Oracle", "Communication", "Leadership"}
_CASE_SENSITIVE_ALIASES = {"node", "spring", "rails", "lambda", "spark", "transformers", "ml", "vue", "mongo"}

_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _aliases in SKILLS.items():
    for _alias in [_canonical, *_aliases]:
        _ALIAS_TO_CANONICAL[_alias.lower()] = _canonical


def _pattern(alias: str) -> str:
    # Word boundaries that also work for names like "C++", "C#" and ".NET".
    return r"(?<![A-Za-z0-9+#.])" + re.escape(alias) + r"(?![A-Za-z0-9+#&])"


_MATCHERS: list[tuple[str, re.Pattern]] = []
for _canonical, _aliases in SKILLS.items():
    for _alias in [_canonical, *_aliases]:
        if _canonical in _CASE_SENSITIVE and _alias == _canonical:
            # e.g. "Go" but not "go", "R" but not "r"
            _MATCHERS.append((_canonical, re.compile(_pattern(_alias))))
        elif _alias in _CASE_SENSITIVE_ALIASES:
            # Ambiguous lowercase alias: require a capitalised form ("Node", "ML").
            _MATCHERS.append((_canonical, re.compile(_pattern(_alias.capitalize()) + "|" + _pattern(_alias.upper()))))
        else:
            _MATCHERS.append((_canonical, re.compile(_pattern(_alias), re.IGNORECASE)))


def canonical_skill(name: str) -> str:
    """Map a free-text skill to its canonical spelling (or tidy it up)."""
    cleaned = re.sub(r"\s+", " ", name).strip(" .,;:-•*")
    return _ALIAS_TO_CANONICAL.get(cleaned.lower(), cleaned)


def skill_key(name: str) -> str:
    """Comparison key so "ReactJS", "react.js" and "React" are equal."""
    return canonical_skill(name).lower()


def normalize_skills(names: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for name in names:
        canonical = canonical_skill(name)
        key = canonical.lower()
        if canonical and key not in seen and len(canonical) <= 60:
            seen.add(key)
            result.append(canonical)
    return result


def find_skills(text: str) -> list[str]:
    """Detect known skills in free text, in vocabulary order."""
    found: list[str] = []
    for canonical, pattern in _MATCHERS:
        if canonical not in found and pattern.search(text):
            found.append(canonical)
    return found
