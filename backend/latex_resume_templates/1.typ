#import "@preview/modern-cv:0.9.0": *

#show: resume.with(
  author: (
    firstname: "First",
    lastname: "Last",
    email: "your.email@example.com",
    phone: "(+XX) XXX-XXX-XXXX",
    github: "your-github-username",
    linkedin: "your-linkedin-username",
    address: "Your Address, City, Country",
    positions: (
      "Current Position Title",
      "Another Position / Role (if relevant)"
    )
  ),
  profile-picture: none,                    # or image("path/to/photo.png")
  date: datetime.today().display(),          # or a custom date string
  paper-size: "us-letter",                    # or "a4"
  # you can also possibly set theme / colors here if supported
)

= Summary / Profile
#resume-item[
  - "A brief summary or professional profile."
  - "One more bullet about your strengths or focus."
  - "Optional: another line or two."
]

= Experience
#resume-entry(
  title: "Company / Organization Name",
  location: "City, Country",
  date: "Month Year – Month Year",
  description: "Short description of the role / company"
)
#resume-item[
  - "Key achievement / responsibility 1"
  - "Key achievement / responsibility 2"
  - "Key achievement / responsibility 3"
]

#resume-entry(
  title: "Another Company / Role",
  location: "City, Country",
  date: "Month Year – Month Year",
  description: "Description for this role"
)
#resume-item[
  - "Achievement / task A"
  - "Achievement / task B"
]

= Education
#resume-entry(
  title: "University / School Name",
  location: "City, Country",
  date: "Month Year – Month Year",
  description: "Degree / Major, any thesis or relevant info"
)
#resume-item[
  - "Relevant coursework or specialization"
  - "Academic achievement or award"
]

= Projects (Optional)
#resume-entry(
  title: "Project Name",
  location: "",                       # optional, maybe company / org
  date: "Month Year",
  description: "Short description of the project"
)
#resume-item[
  - "What you built / contributed"
  - "Technologies used"
  - "Impact or result"
]

= Skills
#resume-item[
  - "Skill Category 1: skill1, skill2, skill3"
  - "Skill Category 2: skill4, skill5"
  - "Skill Category 3: …"
]

= Certifications (Optional)
#resume-entry(
  title: "Certification Name",
  location: "Issuing Organization",
  date: "Month Year",
  description: "Short note about what the certification means or your score"
)

= Awards & Honors (Optional)
#resume-entry(
  title: "Award / Honor Name",
  location: "Organization / Institution",
  date: "Month Year",
  description: "What the award was for"
)

= Languages (Optional)
#resume-item[
  - "Language 1 — Level (e.g. Native / Fluent / Intermediate)"
  - "Language 2 — Level"
]

= Interests (Optional)
#resume-item[
  - "Interest 1 or Hobby"
  - "Interest 2"
  - "Interest 3"
]

= References (Optional)
#resume-entry(
  title: "Reference Name",
  location: "Organization / Relationship",
  date: "",
  description: "Contact info or note (if you want to mention availability)"
)
#resume-item[
  - "Referee email: email@example.com"
  - "Referee phone: (+XX) X-XXXX-XXXX"
]

