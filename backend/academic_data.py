"""
Official Institutional Registry of The University of Bamenda (UBa) and Catholic University of Cameroon (CATUC) Bamenda.
Contains all Faculties, Schools, Institutes, their official names, mottoes, degrees, and departments.
"""
from typing import Optional, Dict, Any, List, Tuple

UNIVERSITIES = {

    "uba": {
        "code": "UBA",
        "name_en": "THE UNIVERSITY OF BAMENDA",
        "name_fr": "L'UNIVERSITÉ DE BAMENDA",
        "motto": "Knowledge, Probity, Entrepreneurship",
        "type": "State University",
        "city": "Bambili, Bamenda",
        "country": "Republic of Cameroon"
    },
    "catuc": {
        "code": "CATUC",
        "name_en": "CATHOLIC UNIVERSITY OF CAMEROON, BAMENDA",
        "name_fr": "UNIVERSITÉ CATHOLIQUE DU CAMEROUN À BAMENDA",
        "motto": "Fides et Scientia (Faith and Knowledge)",
        "type": "Private Catholic University",
        "city": "Bamenda",
        "country": "Republic of Cameroon"
    }
}

UBA_ESTABLISHMENTS = {
    "coltech": {
        "university": "uba",
        "code": "COLTECH",
        "name_en": "COLLEGE OF TECHNOLOGY",
        "name_fr": "COLLÈGE DE TECHNOLOGIE",
        "motto": "Building capacities in innovative technology for development",
        "degrees": ["BTech", "HND", "MTech", "MSc", "PhD"],
        "default_doc_types": ["project_btech", "project_hnd", "dissertation_mtech", "dissertation_bsc", "dissertation_msc", "thesis_phd", "internship", "proposal", "assignment"],
        "departments": [
            "Computer Engineering",
            "Electrical and Electronic Engineering",
            "Mechanical and Industrial Engineering",
            "Civil Engineering and Architecture",
            "Agricultural and Environmental Engineering",
            "Petroleum Engineering",
            "Mining and Mineral Engineering",
            "Chemical and Biochemical Engineering",
            "Forestry and Wildlife Technology",
            "Animal Health and Production Technology",
            "Food and Bioprocess Technology"
        ],
        "department_options": {
            "Computer Engineering": [
                "Software Engineering",
                "Information Technology and Cybersecurity",
                "Computer Networks and Systems",
                "Artificial Intelligence and Data Science"
            ],
            "Electrical and Electronic Engineering": [
                "Power Systems and Renewable Energy",
                "Telecommunications and Networking",
                "Control Systems and Automation"
            ],
            "Mechanical and Industrial Engineering": [
                "Automotive and Thermal Systems",
                "Manufacturing and Industrial Production",
                "Energy and Environmental Systems"
            ],
            "Civil Engineering and Architecture": [
                "Structural Engineering",
                "Geotechnical and Highway Engineering",
                "Water Resources and Environmental Engineering",
                "Architecture and Urban Planning"
            ],
            "Petroleum Engineering": [
                "Drilling and Production Technology",
                "Reservoir Engineering and Management"
            ]
        }
    },
    "fs": {
        "university": "uba",
        "code": "FS",
        "name_en": "FACULTY OF SCIENCE",
        "name_fr": "FACULTÉ DES SCIENCES",
        "motto": "Excellence in Scientific Enquiry and Innovation",
        "degrees": ["BSc", "MSc", "PhD"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "thesis_phd", "internship", "proposal", "assignment"],
        "departments": [
            "Computer Science",
            "Mathematics",
            "Physics",
            "Chemistry",
            "Biochemistry",
            "Animal Biology (Zoology)",
            "Plant Biology (Botany)",
            "Geology, Mining and Environmental Science"
        ]
    },
    "fems": {
        "university": "uba",
        "code": "FEMS",
        "name_en": "FACULTY OF ECONOMICS AND MANAGEMENT SCIENCES",
        "name_fr": "FACULTÉ DES SCIENCES ÉCONOMIQUES ET DE GESTION",
        "motto": "Fostering Economic Development and Enterprise",
        "degrees": ["BSc", "MSc", "PhD"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "thesis_phd", "internship", "proposal", "assignment"],
        "departments": [
            "Economics",
            "Management",
            "Accounting",
            "Banking and Finance",
            "Marketing"
        ]
    },
    "fa": {
        "university": "uba",
        "code": "FA",
        "name_en": "FACULTY OF ARTS",
        "name_fr": "FACULTÉ DES LETTRES ET SCIENCES HUMAINES",
        "motto": "Preserving Culture, Illuminating Humanity",
        "degrees": ["BA", "MA", "PhD"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "thesis_phd", "internship", "proposal", "assignment"],
        "departments": [
            "English",
            "French",
            "History and Archaeology",
            "Geography and Planning",
            "Performing and Visual Arts",
            "Philosophy",
            "Communication and Development Studies",
            "Linguistics and African Languages"
        ]
    },
    "fed": {
        "university": "uba",
        "code": "FED",
        "name_en": "FACULTY OF EDUCATION",
        "name_fr": "FACULTÉ DES SCIENCES DE L'ÉDUCATION",
        "motto": "Empowering Educators for National Transformation",
        "degrees": ["B.Ed", "M.Ed", "PhD"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "thesis_phd", "internship", "proposal", "assignment"],
        "departments": [
            "Educational Psychology",
            "Curriculum and Instruction",
            "Educational Foundations",
            "Educational Leadership and Management",
            "Special Education"
        ]
    },
    "flps": {
        "university": "uba",
        "code": "FLPS",
        "name_en": "FACULTY OF LAWS AND POLITICAL SCIENCE",
        "name_fr": "FACULTÉ DES SCIENCES JURIDIQUES ET POLITIQUES",
        "motto": "Justice, Integrity and the Rule of Law",
        "degrees": ["LL.B", "LL.M", "PhD"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "thesis_phd", "internship", "proposal", "assignment"],
        "departments": [
            "English Private Law",
            "French Private Law",
            "Public Law",
            "Political Science"
        ]
    },
    "fhs": {
        "university": "uba",
        "code": "FHS",
        "name_en": "FACULTY OF HEALTH SCIENCES",
        "name_fr": "FACULTÉ DES SCIENCES DE LA SANTÉ",
        "motto": "Excellence in Healthcare, Training and Biomedical Discovery",
        "degrees": ["MD", "B.N.Sc", "MSc", "PhD"],
        "default_doc_types": ["thesis_phd", "dissertation_msc", "dissertation_bsc", "internship", "proposal"],
        "departments": [
            "Medicine and Surgery",
            "Nursing Science",
            "Medical Laboratory Science",
            "Public Health",
            "Health Economics and Policy"
        ]
    },
    "hicm": {
        "university": "uba",
        "code": "HICM",
        "name_en": "HIGHER INSTITUTE OF COMMERCE AND MANAGEMENT",
        "name_fr": "INSTITUT SUPÉRIEUR DE COMMERCE ET DE MANAGEMENT",
        "motto": "Shaping Ethical Business Leaders",
        "degrees": ["B.Com", "M.Com", "MBA", "PhD"],
        "default_doc_types": ["project_btech", "dissertation_msc", "internship", "proposal", "assignment"],
        "departments": [
            "Accounting and Finance",
            "Marketing and International Trade",
            "Management and Entrepreneurship",
            "Insurance and Security",
            "Human Resource Management"
        ]
    },
    "hitl": {
        "university": "uba",
        "code": "HITL",
        "name_en": "HIGHER INSTITUTE OF TRANSPORT AND LOGISTICS",
        "name_fr": "INSTITUT SUPÉRIEUR DE TRANSPORT ET DE LOGISTIQUE",
        "motto": "Connecting Nations, Moving Economies",
        "degrees": ["B.Tech", "M.Tech", "PhD"],
        "default_doc_types": ["project_btech", "dissertation_mtech", "internship", "proposal", "assignment"],
        "departments": [
            "Land Transport",
            "Maritime Transport",
            "Air Transport",
            "Logistics and Supply Chain Management",
            "Transit and Customs Clearance"
        ]
    },
    "httc": {
        "university": "uba",
        "code": "HTTC",
        "name_en": "HIGHER TECHNICAL TEACHER TRAINING COLLEGE",
        "name_fr": "ÉCOLE NORMALE SUPÉRIEURE DE L'ENSEIGNEMENT TECHNIQUE (ENSET)",
        "motto": "Innovating Technical Pedagogy",
        "degrees": ["DIPET I", "DIPET II"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "internship", "proposal", "assignment"],
        "departments": [
            "Civil Engineering and Forestry",
            "Mechanical Engineering",
            "Electrical and Power Engineering",
            "Computer Science and Information Technology",
            "Administrative Techniques",
            "Economic Sciences and Management",
            "Home Economics and Social Work",
            "Sciences of Education"
        ]
    },
    "ens": {
        "university": "uba",
        "code": "ENS",
        "name_en": "HIGHER TEACHER TRAINING COLLEGE (ENS BAMBILI)",
        "name_fr": "ÉCOLE NORMALE SUPÉRIEURE DE BAMBILI",
        "motto": "Pioneering Pedagogic Excellence",
        "degrees": ["DIPES I", "DIPES II"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "internship", "proposal", "assignment"],
        "departments": [
            "Biology",
            "Chemistry",
            "English Modern Letters",
            "French Modern Letters",
            "Geography",
            "History",
            "Mathematics",
            "Physics",
            "Computer Science",
            "Philosophy",
            "Bilingual Letters"
        ]
    },
    "nahpi": {
        "university": "uba",
        "code": "NAHPI",
        "name_en": "NATIONAL HIGHER POLYTECHNIC INSTITUTE",
        "name_fr": "ÉCOLE NATIONALE SUPÉRIEURE POLYTECHNIQUE",
        "motto": "Engineering Cameroon's Industrial Future",
        "degrees": ["BEng", "MEng", "PhD"],
        "default_doc_types": ["project_btech", "dissertation_mtech", "thesis_phd", "internship", "proposal", "assignment"],
        "departments": [
            "Computer Engineering",
            "Electrical and Electronic Engineering",
            "Civil Engineering",
            "Mechanical Engineering",
            "Chemical and Petroleum Engineering",
            "Mining and Mineral Engineering",
            "Biomedical Engineering"
        ]
    }
}

CATUC_ESTABLISHMENTS = {
    "catuc_seng": {
        "university": "catuc",
        "code": "SENG",
        "name_en": "SCHOOL OF ENGINEERING",
        "name_fr": "ÉCOLE D'INGÉNIERIE",
        "motto": "Innovation with Ethical Grounding",
        "degrees": ["BEng", "BTech", "HND", "MEng"],
        "default_doc_types": ["project_btech", "project_hnd", "dissertation_mtech", "internship", "proposal", "assignment"],
        "departments": [
            "Software Engineering",
            "Computer Engineering",
            "Civil Engineering",
            "Electrical and Electronic Engineering",
            "Mechanical Engineering"
        ]
    },
    "catuc_fbms": {
        "university": "catuc",
        "code": "FBMS",
        "name_en": "FACULTY OF BUSINESS AND MANAGEMENT SCIENCES",
        "name_fr": "FACULTÉ DE GESTION ET DES SCIENCES DE MANAGEMENT",
        "motto": "Ethical Business and Sustainable Development",
        "degrees": ["BSc", "B.Com", "MBA", "MSc", "PhD"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "internship", "proposal", "assignment"],
        "departments": [
            "Accounting",
            "Banking and Finance",
            "Economics",
            "Marketing",
            "Management Sciences"
        ]
    },
    "catuc_fst": {
        "university": "catuc",
        "code": "FST",
        "name_en": "FACULTY OF SCIENCE AND TECHNOLOGY",
        "name_fr": "FACULTÉ DES SCIENCES ET DE LA TECHNOLOGIE",
        "motto": "Scientific Rigour and Practical Impact",
        "degrees": ["BSc", "MSc", "PhD"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "thesis_phd", "internship", "proposal", "assignment"],
        "departments": [
            "Computer Science",
            "Mathematics",
            "Physics",
            "Chemistry",
            "Life Sciences"
        ]
    },
    "catuc_shms": {
        "university": "catuc",
        "code": "SHMS",
        "name_en": "SCHOOL OF HEALTH AND MEDICAL SCIENCES",
        "name_fr": "ÉCOLE DES SCIENCES DE LA SANTÉ ET DE LA MÉDECINE",
        "motto": "Healing with Compassion and Skill",
        "degrees": ["B.N.Sc", "BSc", "MSc"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "internship", "proposal"],
        "departments": [
            "Nursing Science",
            "Medical Laboratory Science",
            "Public Health",
            "Biomedical Sciences",
            "Pharmacy Technology"
        ]
    },
    "catuc_fhss": {
        "university": "catuc",
        "code": "FHSS",
        "name_en": "FACULTY OF HUMANITIES AND SOCIAL SCIENCES",
        "name_fr": "FACULTÉ DES HUMANITÉS ET SCIENCES SOCIALES",
        "motto": "Humanity in Search of Truth and Meaning",
        "degrees": ["BA", "MA", "PhD"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "internship", "proposal", "assignment"],
        "departments": [
            "Anthropology",
            "History",
            "Philosophy",
            "English and Literature",
            "Sociology"
        ]
    },
    "catuc_stanr": {
        "university": "catuc",
        "code": "STANR",
        "name_en": "SCHOOL OF TROPICAL AGRICULTURE AND NATURAL RESOURCES",
        "name_fr": "ÉCOLE D'AGRICULTURE TROPICALE ET RESSOURCES NATURELLES",
        "motto": "Nourishing the Earth and Society",
        "degrees": ["BSc", "MSc"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "internship", "proposal", "assignment"],
        "departments": [
            "Agronomy",
            "Animal Science",
            "Agricultural Economics",
            "Food Science and Technology"
        ]
    },
    "catuc_stheo": {
        "university": "catuc",
        "code": "STHEO",
        "name_en": "SCHOOL OF THEOLOGY",
        "name_fr": "ÉCOLE DE THÉOLOGIE",
        "motto": "Truth in Love",
        "degrees": ["B.Th", "M.Th"],
        "default_doc_types": ["dissertation_bsc", "dissertation_msc", "thesis_phd", "proposal"],
        "departments": [
            "Biblical Studies",
            "Systematic Theology",
            "Moral Theology",
            "Pastoral Theology"
        ]
    }
}

# Unified Establishments Registry
ALL_ESTABLISHMENTS = {**UBA_ESTABLISHMENTS, **CATUC_ESTABLISHMENTS}

DOCUMENT_TYPE_LABELS = {
    "project_btech": "BTech Final Year Project (Bachelor of Technology)",
    "project_hnd": "HND Capstone Project (Higher National Diploma)",
    "dissertation_bsc": "BSc / BA Dissertation (Bachelor of Science / Arts)",
    "dissertation_mtech": "MTech Dissertation / Project (Master of Technology)",
    "dissertation_msc": "MSc / MA Dissertation (Master of Science / Arts)",
    "thesis_phd": "PhD Doctoral Thesis (Doctor of Philosophy)",
    "internship": "Academic Internship Report",
    "proposal": "Research / Project Proposal",
    "assignment": "Course Technical Assignment (with Dual Header)"
}

def resolve_department_and_option(faculty_code: str, raw_dept: str, raw_opt: Optional[str] = None) -> tuple[str, str]:
    """
    Distinguishes and resolves Department vs Option (Specialization).
    Prevents options like 'Information Technology and Cybersecurity' from replacing
    the actual Department 'Computer Engineering' in headers.
    """
    dept = (raw_dept or "").strip()
    opt = (raw_opt or "").strip()

    # If department itself is an option under Computer Engineering
    if any(k in dept.lower() for k in ["information technology", "cybersecurity", "software engineering", "networks"]):
        if not opt:
            opt = dept
        dept = "Computer Engineering"

    # If department is an option under Electrical Engineering
    elif any(k in dept.lower() for k in ["power systems", "telecommunications"]):
        if not opt:
            opt = dept
        dept = "Electrical and Electronic Engineering"

    # If option is missing or identical to department, provide standard default or keep clean
    if not opt:
        opt = dept

    return dept, opt

