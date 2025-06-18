import datetime
import logging
from enum import Enum
from typing import List, Optional

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field, ValidationError

from fh_pydantic_form import (
    ComparisonForm,
    ComparisonMap,
    ComparisonMetric,
    comparison_form_js,
    list_manipulation_js,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        list_manipulation_js(),
        comparison_form_js(),  # Add comparison-specific JS
    ],
    pico=False,
    live=True,
)


# ============================================================================
# Data Models for Resume Extraction
# ============================================================================


class ProficiencyLevel(Enum):
    NATIVE = "Native"
    FLUENT = "Fluent"
    PROFESSIONAL = "Professional"
    CONVERSATIONAL = "Conversational"
    BASIC = "Basic"


class ContactInfo(BaseModel):
    email: str = Field(description="Professional email address")
    phone: Optional[str] = Field(None, description="Phone number")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    github: Optional[str] = Field(None, description="GitHub profile URL")

    def __str__(self) -> str:
        return f"{self.email}" + (f" | {self.phone}" if self.phone else "")


class WorkExperience(BaseModel):
    company: str = Field(description="Company name")
    position: str = Field(description="Job title")
    start_date: datetime.date = Field(description="Start date")
    end_date: Optional[datetime.date] = Field(
        None, description="End date (None if current)"
    )
    responsibilities: List[str] = Field(
        default_factory=list, description="Key responsibilities"
    )
    technologies: List[str] = Field(
        default_factory=list, description="Technologies used"
    )

    def __str__(self) -> str:
        end = "Present" if self.end_date is None else str(self.end_date.year)
        return f"{self.position} at {self.company} ({self.start_date.year}-{end})"


class Education(BaseModel):
    institution: str = Field(description="University/School name")
    degree: str = Field(description="Degree obtained")
    field_of_study: str = Field(description="Major/Field")
    graduation_year: int = Field(description="Graduation year")
    gpa: Optional[float] = Field(None, description="Grade Point Average")
    honors: List[str] = Field(default_factory=list, description="Honors and awards")

    def __str__(self) -> str:
        return f"{self.degree} in {self.field_of_study} from {self.institution} ({self.graduation_year})"


class SkillCategory(BaseModel):
    programming_languages: List[str] = Field(
        default_factory=list, description="Programming languages"
    )
    frameworks: List[str] = Field(
        default_factory=list, description="Frameworks and libraries"
    )
    databases: List[str] = Field(
        default_factory=list, description="Database technologies"
    )
    tools: List[str] = Field(default_factory=list, description="Development tools")
    cloud_platforms: List[str] = Field(
        default_factory=list, description="Cloud platforms"
    )

    def __str__(self) -> str:
        total = (
            len(self.programming_languages) + len(self.frameworks) + len(self.databases)
        )
        return f"{total} technical skills"


class Project(BaseModel):
    name: str = Field(description="Project name")
    description: str = Field(description="Project description")
    technologies: List[str] = Field(
        default_factory=list, description="Technologies used"
    )
    url: Optional[str] = Field(None, description="Project URL")
    outcomes: Optional[str] = Field(None, description="Key outcomes/metrics")

    def __str__(self) -> str:
        return f"{self.name} ({len(self.technologies)} technologies)"


class Publication(BaseModel):
    title: str = Field(description="Publication title")
    venue: str = Field(description="Journal/Conference")
    year: int = Field(description="Publication year")
    authors: List[str] = Field(default_factory=list, description="List of authors")
    url: Optional[str] = Field(None, description="Publication URL/DOI")

    def __str__(self) -> str:
        return f"{self.title} ({self.venue}, {self.year})"


class Language(BaseModel):
    language: str = Field(description="Language name")
    proficiency: ProficiencyLevel = Field(description="Proficiency level")

    def __str__(self) -> str:
        return f"{self.language} ({self.proficiency.value})"


class ExtractedResume(BaseModel):
    """Complete extracted resume model with multiple nesting levels"""

    # Basic Information
    full_name: str = Field(description="Full name")
    professional_title: str = Field(description="Current professional title")
    summary: str = Field(description="Professional summary")

    # Contact (nested model)
    contact: ContactInfo = Field(description="Contact information")

    # Experience (list of nested models)
    experience: List[WorkExperience] = Field(
        default_factory=list, description="Work experience"
    )

    # Education (list of nested models)
    education: List[Education] = Field(
        default_factory=list, description="Educational background"
    )

    # Skills (nested model with lists)
    skills: SkillCategory = Field(
        default_factory=SkillCategory, description="Technical skills"
    )

    # Projects (list of nested models)
    projects: List[Project] = Field(
        default_factory=list, description="Notable projects"
    )

    # Publications (list of nested models)
    publications: List[Publication] = Field(
        default_factory=list, description="Publications"
    )

    # Languages (list of nested models)
    languages: List[Language] = Field(
        default_factory=list, description="Language proficiencies"
    )

    # Meta fields
    extraction_confidence: float = Field(
        0.0, description="Overall extraction confidence score"
    )
    extraction_timestamp: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        description="When extraction was performed",
    )


# ============================================================================
# Evaluation Metrics Generation
# ============================================================================


def create_evaluation_metrics() -> ComparisonMap:
    """
    Simulate comprehensive metrics from an LLM extraction evaluation framework.
    Keys use dot notation for nested fields and bracket notation for list indices.
    """
    return {
        # Top-level fields
        "full_name": ComparisonMetric(
            metric=0.95,
            comment="High confidence match with fuzzy string matching",
        ),
        "professional_title": ComparisonMetric(
            metric=0.80,
            comment="Minor variation: 'Senior Engineer' vs 'Sr. Engineer'",
        ),
        "summary": ComparisonMetric(
            metric=0.72,
            comment="LLM paraphrased instead of extracting verbatim",
        ),
        # Nested BaseModel fields (ContactInfo)
        "contact": ComparisonMetric(
            metric=0.85,
            comment="Contact section overall: 3/4 fields extracted",
        ),
        "contact.email": ComparisonMetric(
            metric=1.0, comment="Email extracted exactly"
        ),
        "contact.phone": ComparisonMetric(
            metric=0.0, comment="Phone number not found in source document"
        ),
        "contact.linkedin": ComparisonMetric(
            metric=0.9, comment="LinkedIn URL normalized correctly"
        ),
        "contact.github": ComparisonMetric(
            metric=1.0, comment="GitHub profile extracted"
        ),
        # Work Experience - First job
        "experience": ComparisonMetric(
            metric=0.45,
            comment="Experience section: 2 positions extracted with some missing details",
        ),
        "experience[0]": ComparisonMetric(
            metric=0.85, comment="Most recent position well extracted"
        ),
        "experience[0].company": ComparisonMetric(
            metric=1.0, comment="Company name exact match"
        ),
        "experience[0].position": ComparisonMetric(
            metric=0.95,
            comment="Title normalized: 'Sr.' expanded to 'Senior'",
        ),
        "experience[0].start_date": ComparisonMetric(
            metric=1.0, comment="Start date parsed correctly"
        ),
        "experience[0].end_date": ComparisonMetric(
            metric=0.0, comment="Current position not marked as None"
        ),
        "experience[0].responsibilities": ComparisonMetric(
            metric=0.40, comment="2 of 3 key responsibilities captured"
        ),
        "experience[0].responsibilities[0]": ComparisonMetric(
            metric=0.9,
            comment="Leadership responsibility captured accurately",
        ),
        "experience[0].responsibilities[1]": ComparisonMetric(
            metric=0.7,
            comment="Technical detail paraphrased: 'Architected' → 'Designed'",
        ),
        "experience[0].responsibilities[2]": ComparisonMetric(
            metric=0.0, comment="Performance metric (70% reduction) missed"
        ),
        "experience[0].technologies": ComparisonMetric(
            metric=0.8, comment="4 of 5 key technologies identified"
        ),
        # Work Experience - Second job
        "experience[1]": ComparisonMetric(
            metric=0.65,
            comment="Older position with incomplete extraction",
        ),
        "experience[1].company": ComparisonMetric(
            metric=0.8,
            comment="Company name variation: missing subsidiary info",
        ),
        "experience[1].position": ComparisonMetric(
            metric=1.0, comment="Position title exact match"
        ),
        "experience[1].responsibilities": ComparisonMetric(
            metric=0.5, comment="Only 50% of responsibilities found"
        ),
        # Education
        "education": ComparisonMetric(
            metric=0.92, comment="Education section well extracted"
        ),
        "education[0]": ComparisonMetric(
            metric=0.95, comment="Primary degree extracted accurately"
        ),
        "education[0].institution": ComparisonMetric(
            metric=1.0, comment="University name correct"
        ),
        "education[0].degree": ComparisonMetric(
            metric=1.0, comment="Degree type matched"
        ),
        "education[0].field_of_study": ComparisonMetric(
            metric=0.9,
            comment="Field normalized: 'CS' → 'Computer Science'",
        ),
        "education[0].gpa": ComparisonMetric(
            metric=0.0, comment="GPA not mentioned in source document"
        ),
        "education[0].honors": ComparisonMetric(
            metric=0.8,
            comment="1 of 2 honors extracted (Dean's List found)",
        ),
        # Skills section with nested lists
        "skills": ComparisonMetric(
            metric=0.75,
            comment="Skills section: good coverage with some categorization errors",
        ),
        "skills.programming_languages": ComparisonMetric(
            metric=0.85,
            comment="Most programming languages identified correctly",
        ),
        "skills.programming_languages[0]": ComparisonMetric(
            metric=1.0, comment="'Python' identified correctly"
        ),
        "skills.programming_languages[1]": ComparisonMetric(
            metric=0.9, comment="Normalized: 'JavaScript' from 'JS'"
        ),
        "skills.programming_languages[2]": ComparisonMetric(
            metric=0.0, comment="'Go' language missed in extraction"
        ),
        "skills.frameworks": ComparisonMetric(
            metric=0.6,
            comment="Some frameworks misclassified as libraries",
        ),
        "skills.databases": ComparisonMetric(
            metric=0.9, comment="Database technologies well identified"
        ),
        "skills.tools": ComparisonMetric(
            metric=0.7, comment="Development tools partially extracted"
        ),
        "skills.cloud_platforms": ComparisonMetric(
            metric=1.0,
            comment="All cloud platforms correctly identified",
        ),
        # Projects
        "projects": ComparisonMetric(
            metric=0.82, comment="Projects section well structured"
        ),
        "projects[0]": ComparisonMetric(
            metric=0.88, comment="Main project comprehensively extracted"
        ),
        "projects[0].name": ComparisonMetric(
            metric=1.0, comment="Project name exact match"
        ),
        "projects[0].description": ComparisonMetric(
            metric=0.85,
            comment="Description captured with minor paraphrasing",
        ),
        "projects[0].technologies": ComparisonMetric(
            metric=0.9, comment="9 of 10 technologies identified"
        ),
        "projects[0].technologies[1]": ComparisonMetric(
            metric=0.8,
            comment="Version info lost: 'Node.js 18' → 'Node.js'",
        ),
        "projects[0].outcomes": ComparisonMetric(
            metric=0.7,
            comment="Quantitative metrics partially captured",
        ),
        # Publications
        "publications": ComparisonMetric(
            metric=0.6,
            comment="Academic publications challenging to extract",
        ),
        "publications[0]": ComparisonMetric(
            metric=0.75,
            comment="Primary publication with some missing details",
        ),
        "publications[0].title": ComparisonMetric(
            metric=0.95,
            comment="Title extracted with minor formatting differences",
        ),
        "publications[0].venue": ComparisonMetric(
            metric=0.8,
            comment="Conference acronym expanded incorrectly",
        ),
        "publications[0].authors": ComparisonMetric(
            metric=0.7, comment="2 of 4 co-authors missing"
        ),
        "publications[0].authors[0]": ComparisonMetric(
            metric=1.0,
            comment="Primary author (candidate) correctly identified",
        ),
        # Languages
        "languages": ComparisonMetric(
            metric=0.85, comment="Language proficiencies well extracted"
        ),
        "languages[0]": ComparisonMetric(
            metric=0.95, comment="Primary language captured"
        ),
        "languages[0].language": ComparisonMetric(
            metric=1.0, comment="'English' identified"
        ),
        "languages[0].proficiency": ComparisonMetric(
            metric=0.9, comment="Proficiency mapped to enum correctly"
        ),
        # Metadata
        "extraction_confidence": ComparisonMetric(
            metric=0.76,
            comment="Overall extraction confidence score: 76%",
        ),
        "extraction_timestamp": ComparisonMetric(
            metric=1.0, comment="Timestamp auto-generated"
        ),
    }


# ============================================================================
# Sample Data Creation
# ============================================================================


def create_reference_resume() -> ExtractedResume:
    """Create the reference (ground truth) resume data"""
    return ExtractedResume(
        full_name="Dr. Jane Elizabeth Smith",
        professional_title="Senior Software Engineer & Tech Lead",
        summary=(
            "Accomplished software engineer with 8+ years of experience leading cross-functional teams "
            "and architecting scalable systems. Expertise in cloud-native applications, microservices, "
            "and machine learning infrastructure. Passionate about mentoring and building inclusive teams."
        ),
        contact=ContactInfo(
            email="jane.smith@email.com",
            phone="+1-555-123-4567",
            linkedin="https://linkedin.com/in/janesmith",
            github="https://github.com/janesmith",
        ),
        experience=[
            WorkExperience(
                company="TechCorp Inc.",
                position="Senior Software Engineer",
                start_date=datetime.date(2020, 3, 1),
                end_date=None,  # Current position
                responsibilities=[
                    "Led team of 5 engineers in developing microservices platform",
                    "Architected event-driven system processing 1M+ events/day",
                    "Reduced deployment time by 70% through CI/CD improvements",
                ],
                technologies=["Python", "Go", "Kubernetes", "AWS", "PostgreSQL"],
            ),
            WorkExperience(
                company="DataSystems Global LLC",
                position="Software Engineer II",
                start_date=datetime.date(2018, 6, 1),
                end_date=datetime.date(2020, 2, 28),
                responsibilities=[
                    "Developed RESTful APIs serving 10K+ requests/minute",
                    "Implemented caching layer reducing database load by 60%",
                    "Mentored 2 junior developers and led code review sessions",
                    "Contributed to open-source projects and internal tools",
                ],
                technologies=["Java", "Spring Boot", "Redis", "MySQL", "Docker"],
            ),
        ],
        education=[
            Education(
                institution="Stanford University",
                degree="Master of Science",
                field_of_study="Computer Science",
                graduation_year=2018,
                gpa=3.9,
                honors=["Dean's List", "Graduate Research Fellowship"],
            ),
            Education(
                institution="UC Berkeley",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                graduation_year=2016,
                gpa=3.85,
                honors=["Summa Cum Laude", "Phi Beta Kappa"],
            ),
        ],
        skills=SkillCategory(
            programming_languages=["Python", "JavaScript", "Go", "Java", "Rust"],
            frameworks=["Django", "React", "FastAPI", "Spring Boot", "Next.js"],
            databases=["PostgreSQL", "MongoDB", "Redis", "Elasticsearch"],
            tools=["Git", "Docker", "Kubernetes", "Terraform", "Jenkins"],
            cloud_platforms=["AWS", "GCP", "Azure"],
        ),
        projects=[
            Project(
                name="ML Pipeline Orchestrator",
                description="Built end-to-end ML pipeline orchestration system handling model training, validation, and deployment",
                technologies=[
                    "Python",
                    "Kubernetes",
                    "Airflow",
                    "MLflow",
                    "TensorFlow",
                    "Redis",
                    "PostgreSQL",
                    "React",
                    "GraphQL",
                    "Docker",
                ],
                url="https://github.com/janesmith/ml-orchestrator",
                outcomes="Reduced model deployment time from days to hours, serving 50+ data scientists",
            ),
            Project(
                name="Real-time Analytics Dashboard",
                description="Developed real-time analytics dashboard for monitoring system performance",
                technologies=["React", "D3.js", "WebSocket", "Node.js", "InfluxDB"],
                url=None,
                outcomes="Provided insights that reduced system downtime by 40%",
            ),
        ],
        publications=[
            Publication(
                title="Scalable Event Processing in Distributed Systems",
                venue="IEEE International Conference on Cloud Computing",
                year=2022,
                authors=["Jane Smith", "Robert Johnson", "Maria Garcia", "David Chen"],
                url="https://doi.org/10.1109/CLOUD.2022.00123",
            )
        ],
        languages=[
            Language(language="English", proficiency=ProficiencyLevel.NATIVE),
            Language(language="Spanish", proficiency=ProficiencyLevel.PROFESSIONAL),
            Language(language="Mandarin", proficiency=ProficiencyLevel.CONVERSATIONAL),
        ],
        extraction_confidence=1.0,  # Perfect for reference
    )


def create_extracted_resume() -> ExtractedResume:
    """Create the LLM-extracted resume data with realistic variations and errors"""
    return ExtractedResume(
        full_name="Jane Smith",  # Missing middle name and title
        professional_title="Sr. Software Engineer",  # Abbreviated, missing "Tech Lead"
        summary=(
            "Experienced software engineer with 8 years leading teams and building scalable systems. "
            "Expert in cloud applications and microservices. Enjoys mentoring."
            # Paraphrased and shortened
        ),
        contact=ContactInfo(
            email="jane.smith@email.com",
            phone=None,  # Failed to extract
            linkedin="linkedin.com/in/janesmith",  # Missing https://
            github="https://github.com/janesmith",
        ),
        experience=[
            WorkExperience(
                company="TechCorp Inc.",  # Correct
                position="Senior Software Engineer",  # Correct
                start_date=datetime.date(2020, 3, 1),  # Correct
                end_date=datetime.date(2023, 12, 31),  # Wrong - should be None
                responsibilities=[
                    "Led team of 5 engineers in developing microservices platform",  # Exact
                    "Designed event-driven system for processing events",  # Paraphrased, missing scale
                    # Missing third responsibility about deployment improvements
                ],
                technologies=[
                    "Python",
                    "Kubernetes",
                    "AWS",
                    "PostgreSQL",
                ],  # Missing Go
            ),
            WorkExperience(
                company="DataSystems Global",  # Missing "LLC"
                position="Software Engineer II",
                start_date=datetime.date(2018, 6, 1),
                end_date=datetime.date(2020, 2, 28),
                responsibilities=[
                    "Developed REST APIs",  # Simplified, missing scale
                    "Implemented caching to reduce database load",  # Missing percentage
                    # Missing last two responsibilities
                ],
                technologies=[
                    "Java",
                    "Spring",
                    "Redis",
                    "MySQL",
                ],  # Spring instead of Spring Boot, missing Docker
            ),
        ],
        education=[
            Education(
                institution="Stanford University",
                degree="Master of Science",
                field_of_study="Computer Science",  # Expanded from "CS"
                graduation_year=2018,
                gpa=None,  # GPA not extracted
                honors=["Dean's List"],  # Missing Graduate Research Fellowship
            ),
            # Missing second education entry (Bachelor's from UC Berkeley)
        ],
        skills=SkillCategory(
            programming_languages=[
                "Python",
                "JS",
                "Java",
                "Rust",
            ],  # JS instead of JavaScript, missing Go
            frameworks=[
                "Django",
                "React",
                "FastAPI",
                "Bootstrap",
            ],  # Bootstrap wrongly categorized, missing Spring Boot
            databases=["PostgreSQL", "MongoDB", "Redis"],  # Missing Elasticsearch
            tools=["Git", "Docker", "Terraform"],  # Missing Kubernetes and Jenkins
            cloud_platforms=["AWS", "GCP", "Azure"],  # All correct
        ),
        projects=[
            Project(
                name="ML Pipeline Orchestrator",
                description="Created ML pipeline system for model training and deployment",  # Simplified
                technologies=[
                    "Python",
                    "Kubernetes",
                    "Airflow",
                    "MLflow",
                    "TensorFlow",
                    "Redis",
                    "PostgreSQL",
                    "React",
                    "Docker",
                ],  # Missing GraphQL
                url="https://github.com/janesmith/ml-orchestrator",
                outcomes="Reduced deployment time, used by data science team",  # Vague, missing specifics
            ),
            # Missing second project
        ],
        publications=[
            Publication(
                title="Scalable Event Processing in Distributed Systems",  # Correct
                venue="IEEE Cloud Computing Conference",  # Incorrect expansion
                year=2022,
                authors=["Jane Smith", "Robert Johnson"],  # Missing 2 co-authors
                url=None,  # DOI not extracted
            )
        ],
        languages=[
            Language(language="English", proficiency=ProficiencyLevel.NATIVE),
            Language(
                language="Spanish", proficiency=ProficiencyLevel.FLUENT
            ),  # Wrong level
            # Missing Mandarin
        ],
        extraction_confidence=0.76,
    )


# ============================================================================
# Metric Analysis Functions
# ============================================================================


def calculate_extraction_summary(metrics: ComparisonMap) -> dict:
    """Calculate summary statistics from the comparison metrics"""
    total_fields = len(metrics)
    perfect_matches = sum(
        1
        for m in metrics.values()
        if isinstance(m.metric, (int, float)) and m.metric == 1.0
    )
    good_matches = sum(
        1
        for m in metrics.values()
        if isinstance(m.metric, (int, float)) and m.metric >= 0.8
    )
    failed_extractions = sum(
        1
        for m in metrics.values()
        if isinstance(m.metric, (int, float)) and m.metric == 0.0 and m.color != "gray"
    )

    # Calculate section-specific scores
    section_scores: dict[str, list[float]] = {
        "contact": [],
        "experience": [],
        "education": [],
        "skills": [],
        "projects": [],
        "publications": [],
        "languages": [],
    }

    for path, metric in metrics.items():
        for section in section_scores:
            if path.startswith(section):
                if isinstance(metric.metric, (int, float)):
                    section_scores[section].append(float(metric.metric))

    # Calculate averages for each section
    section_averages: dict[str, float] = {}
    for section, scores in section_scores.items():
        if scores:
            section_averages[section] = sum(scores) / len(scores)
        else:
            section_averages[section] = 0.0

    # Overall average (excluding gray/NA fields)
    valid_metrics = [
        float(m.metric)
        for m in metrics.values()
        if isinstance(m.metric, (int, float)) and m.color != "gray"
    ]
    overall_accuracy = sum(valid_metrics) / len(valid_metrics) if valid_metrics else 0.0

    return {
        "overall_accuracy": overall_accuracy,
        "total_fields": total_fields,
        "perfect_matches": perfect_matches,
        "good_matches": good_matches,
        "failed_extractions": failed_extractions,
        "section_scores": section_averages,
    }


def get_critical_failures(metrics: ComparisonMap) -> List[tuple[str, ComparisonMetric]]:
    """Identify critical extraction failures"""
    critical_fields = [
        "full_name",
        "contact.email",
        "experience[0].company",
        "experience[0].position",
        "education[0].institution",
    ]

    failures: List[tuple[str, ComparisonMetric]] = []
    for field in critical_fields:
        if field in metrics:
            metric = metrics[field]
            if isinstance(metric.metric, (int, float)) and float(metric.metric) < 0.8:
                failures.append((field, metric))

    return failures


# ============================================================================
# Routes and UI
# ============================================================================


# Create the comparison form
comparison_form = ComparisonForm(
    name="resume_extraction",
    model_class=ExtractedResume,
    left_initial=create_reference_resume(),
    right_initial=create_extracted_resume(),
    comparison=create_evaluation_metrics(),
    disabled_left=False,  # Allow editing reference
    disabled_right=False,  # Allow editing extracted
    left_label="📋 Reference Resume (Ground Truth)",
    right_label="🤖 LLM Extracted Resume",
    spacing="compact",  # Use compact spacing for dense information
    exclude_fields=["extraction_timestamp"],  # Hide timestamp field
)

# Register routes
comparison_form.register_routes(app)


@rt("/")
def get():
    # Calculate summary statistics
    metrics = create_evaluation_metrics()
    summary = calculate_extraction_summary(metrics)
    critical_failures = get_critical_failures(metrics)

    return fh.Div(
        mui.Container(
            # Header
            mui.Card(
                mui.CardHeader(
                    fh.H1(
                        "🔍 LLM Resume Extraction Evaluation",
                        cls="text-2xl font-bold text-blue-600",
                    ),
                    fh.P(
                        "Compare reference resume data with LLM-extracted results using ComparisonForm",
                        cls="text-gray-600 mt-2",
                    ),
                ),
                mui.CardBody(
                    # Summary Statistics Card
                    mui.Card(
                        mui.CardHeader(
                            fh.H2("📊 Extraction Summary", cls="text-lg font-semibold")
                        ),
                        mui.CardBody(
                            # Overall Score with visual indicator
                            fh.Div(
                                fh.Div(
                                    fh.H3(
                                        f"{summary['overall_accuracy']:.1%}",
                                        cls="text-3xl font-bold "
                                        + (
                                            "text-green-600"
                                            if summary["overall_accuracy"] >= 0.8
                                            else "text-yellow-600"
                                            if summary["overall_accuracy"] >= 0.6
                                            else "text-red-600"
                                        ),
                                    ),
                                    fh.P(
                                        "Overall Extraction Accuracy",
                                        cls="text-sm text-gray-600",
                                    ),
                                    cls="text-center",
                                ),
                                cls="mb-4 p-4 bg-gray-50 rounded",
                            ),
                            # Key Metrics Grid
                            fh.Div(
                                fh.Div(
                                    fh.Span(
                                        f"{summary['perfect_matches']}",
                                        cls="text-2xl font-bold text-green-600",
                                    ),
                                    fh.Span(
                                        " Perfect Matches", cls="text-sm text-gray-600"
                                    ),
                                    cls="text-center",
                                ),
                                fh.Div(
                                    fh.Span(
                                        f"{summary['good_matches']}",
                                        cls="text-2xl font-bold text-blue-600",
                                    ),
                                    fh.Span(
                                        " Good Matches (80%+)",
                                        cls="text-sm text-gray-600",
                                    ),
                                    cls="text-center",
                                ),
                                fh.Div(
                                    fh.Span(
                                        f"{summary['failed_extractions']}",
                                        cls="text-2xl font-bold text-red-600",
                                    ),
                                    fh.Span(
                                        " Failed Extractions",
                                        cls="text-sm text-gray-600",
                                    ),
                                    cls="text-center",
                                ),
                                fh.Div(
                                    fh.Span(
                                        f"{summary['total_fields']}",
                                        cls="text-2xl font-bold text-gray-600",
                                    ),
                                    fh.Span(
                                        " Total Fields", cls="text-sm text-gray-600"
                                    ),
                                    cls="text-center",
                                ),
                                cls="grid grid-cols-4 gap-4 mb-4",
                            ),
                            # Section Breakdown
                            fh.Div(
                                fh.H4("Section Breakdown:", cls="font-semibold mb-2"),
                                fh.Div(
                                    *[
                                        fh.Div(
                                            fh.Span(
                                                section.capitalize(), cls="font-medium"
                                            ),
                                            fh.Span(
                                                f": {score:.1%}",
                                                cls=(
                                                    "text-green-600"
                                                    if score >= 0.8
                                                    else "text-yellow-600"
                                                    if score >= 0.6
                                                    else "text-red-600"
                                                ),
                                            ),
                                            cls="flex justify-between",
                                        )
                                        for section, score in summary[
                                            "section_scores"
                                        ].items()
                                    ],
                                    cls="space-y-1 text-sm",
                                ),
                                cls="bg-gray-50 p-3 rounded",
                            ),
                            # Critical Failures Alert
                            (
                                mui.Alert(
                                    fh.Div(
                                        fh.H4(
                                            "⚠️ Critical Field Failures:",
                                            cls="font-semibold mb-1",
                                        ),
                                        fh.Ul(
                                            *[
                                                fh.Li(
                                                    fh.Strong(
                                                        field.replace("_", " ").title()
                                                        + ": "
                                                    ),
                                                    metric.comment,
                                                    cls="text-sm",
                                                )
                                                for field, metric in critical_failures
                                            ],
                                            cls="list-disc list-inside space-y-1",
                                        ),
                                    ),
                                    cls=mui.AlertT.warning + " mt-4",
                                )
                                if critical_failures
                                else ""
                            ),
                        ),
                        cls="mb-4",
                    ),
                    # Metrics Legend
                    mui.Details(
                        mui.Summary(
                            "📖 Metrics Color Legend", cls="cursor-pointer font-medium"
                        ),
                        fh.Div(
                            fh.Div(
                                fh.Span("●", cls="text-green-600 text-xl mr-2"),
                                fh.Span("Excellent (95-100%): ", cls="font-medium"),
                                fh.Span("Near-perfect extraction", cls="text-gray-600"),
                                cls="flex items-center",
                            ),
                            fh.Div(
                                fh.Span("●", cls="text-lime-600 text-xl mr-2"),
                                fh.Span("Good (80-95%): ", cls="font-medium"),
                                fh.Span(
                                    "Minor variations or normalizations",
                                    cls="text-gray-600",
                                ),
                                cls="flex items-center",
                            ),
                            fh.Div(
                                fh.Span("●", cls="text-yellow-600 text-xl mr-2"),
                                fh.Span("Acceptable (60-80%): ", cls="font-medium"),
                                fh.Span(
                                    "Partial extraction or paraphrasing",
                                    cls="text-gray-600",
                                ),
                                cls="flex items-center",
                            ),
                            fh.Div(
                                fh.Span("●", cls="text-orange-600 text-xl mr-2"),
                                fh.Span("Poor (40-60%): ", cls="font-medium"),
                                fh.Span(
                                    "Significant information loss", cls="text-gray-600"
                                ),
                                cls="flex items-center",
                            ),
                            fh.Div(
                                fh.Span("●", cls="text-red-600 text-xl mr-2"),
                                fh.Span("Failed (0-40%): ", cls="font-medium"),
                                fh.Span(
                                    "Extraction failure or major errors",
                                    cls="text-gray-600",
                                ),
                                cls="flex items-center",
                            ),
                            fh.Div(
                                fh.Span("●", cls="text-gray-600 text-xl mr-2"),
                                fh.Span("N/A: ", cls="font-medium"),
                                fh.Span(
                                    "Not applicable or not in source",
                                    cls="text-gray-600",
                                ),
                                cls="flex items-center",
                            ),
                            cls="space-y-2 mt-2",
                        ),
                        cls="mb-4",
                    ),
                ),
            ),
            # Main Comparison Form
            mui.Card(
                mui.CardHeader(
                    fh.H2("🆚 Side-by-Side Comparison", cls="text-xl font-bold"),
                    fh.P(
                        "Visual comparison with metric indicators. Hover over fields to see extraction details.",
                        cls="text-sm text-gray-600",
                    ),
                ),
                mui.CardBody(
                    comparison_form.form_wrapper(
                        fh.Div(
                            comparison_form.render_inputs(),
                            fh.Div(
                                mui.Button(
                                    "🔍 Validate Both",
                                    type="submit",
                                    cls=mui.ButtonT.primary,
                                ),
                                comparison_form.refresh_button("🔄 Refresh"),
                                comparison_form.reset_button("↩️ Reset"),
                                mui.Button(
                                    "📈 Show Only Errors",
                                    onclick="filterErrors()",
                                    type="button",
                                    cls=mui.ButtonT.secondary,
                                ),
                                mui.Button(
                                    "👁️ Show All",
                                    onclick="showAll()",
                                    type="button",
                                    cls=mui.ButtonT.secondary,
                                ),
                                cls="mt-4 flex items-center gap-2 flex-wrap",
                            ),
                            hx_post="/validate_comparison",
                            hx_target="#validation-result",
                            hx_swap="innerHTML",
                        )
                    )
                ),
                cls="mb-4",
            ),
            # Validation Result Area
            fh.Div(id="validation-result"),
            # JavaScript for filtering
            fh.Script("""
                function filterErrors() {
                    // Hide all fields with good metrics (green/lime)
                    document.querySelectorAll('[style*="background-color: #10b981"], [style*="background-color: #84cc16"]').forEach(el => {
                        el.closest('.mb-4, .mb-2, .mb-0')?.classList.add('hidden');
                    });
                }
                
                function showAll() {
                    // Show all hidden fields
                    document.querySelectorAll('.hidden').forEach(el => {
                        el.classList.remove('hidden');
                    });
                }
            """),
        ),
        cls="min-h-screen bg-gray-50 py-8",
    )


@rt("/validate_comparison")
async def post_validate_comparison(req):
    """Validate both forms and show comparison results"""
    try:
        # Parse form data
        form_data = await req.form()
        form_dict = dict(form_data)

        # Validate both forms
        left_valid = True
        right_valid = True
        left_errors: ValidationError | None = None
        right_errors: ValidationError | None = None

        try:
            left_data = comparison_form.left_form.parse(form_dict)
            left_model = ExtractedResume.model_validate(left_data)
        except ValidationError as e:
            left_valid = False
            left_errors = e

        try:
            right_data = comparison_form.right_form.parse(form_dict)
            right_model = ExtractedResume.model_validate(right_data)
        except ValidationError as e:
            right_valid = False
            right_errors = e

        # Display results
        if left_valid and right_valid:
            return mui.Card(
                mui.CardHeader(fh.H3("✅ Both Forms Valid", cls="text-green-600")),
                mui.CardBody(
                    fh.P(
                        "Both reference and extracted data passed validation!",
                        cls="text-lg",
                    ),
                    fh.Div(
                        fh.Div(
                            fh.H4("Reference Summary:", cls="font-semibold"),
                            fh.Pre(
                                f"Name: {left_model.full_name}\n"
                                f"Title: {left_model.professional_title}\n"
                                f"Experience: {len(left_model.experience)} positions\n"
                                f"Skills: {len(left_model.skills.programming_languages)} languages",
                                cls="bg-gray-100 p-2 rounded text-sm mt-1",
                            ),
                            cls="flex-1",
                        ),
                        fh.Div(
                            fh.H4("Extracted Summary:", cls="font-semibold"),
                            fh.Pre(
                                f"Name: {right_model.full_name}\n"
                                f"Title: {right_model.professional_title}\n"
                                f"Experience: {len(right_model.experience)} positions\n"
                                f"Skills: {len(right_model.skills.programming_languages)} languages",
                                cls="bg-gray-100 p-2 rounded text-sm mt-1",
                            ),
                            cls="flex-1",
                        ),
                        cls="grid grid-cols-2 gap-4 mt-2",
                    ),
                ),
                cls="mt-4",
            )
        else:
            # Show validation errors
            return fh.Div(
                mui.Card(
                    mui.CardHeader(fh.H3("❌ Validation Errors", cls="text-red-600")),
                    mui.CardBody(
                        fh.Div(
                            fh.Div(
                                fh.H4("Reference Form:", cls="font-semibold"),
                                (
                                    mui.Alert("✓ Valid", cls=mui.AlertT.success)
                                    if left_valid
                                    else fh.Pre(
                                        left_errors.json(indent=2)
                                        if left_errors
                                        else "Unknown error",
                                        cls="bg-red-50 p-2 rounded text-xs",
                                    )
                                ),
                                cls="flex-1",
                            ),
                            fh.Div(
                                fh.H4("Extracted Form:", cls="font-semibold"),
                                (
                                    mui.Alert("✓ Valid", cls=mui.AlertT.success)
                                    if right_valid
                                    else fh.Pre(
                                        right_errors.json(indent=2)
                                        if right_errors
                                        else "Unknown error",
                                        cls="bg-red-50 p-2 rounded text-xs",
                                    )
                                ),
                                cls="flex-1",
                            ),
                            cls="grid grid-cols-2 gap-4",
                        )
                    ),
                ),
                cls="mt-4",
            )

    except Exception as e:
        return mui.Alert(
            f"Error processing comparison: {str(e)}", cls=mui.AlertT.error + " mt-4"
        )


if __name__ == "__main__":
    fh.serve()
