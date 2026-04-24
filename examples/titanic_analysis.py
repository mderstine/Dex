#!/usr/bin/env python3
"""Example end-to-end Dex analysis flow using public data.

This example demonstrates:
1. Loading local data (simulated public dataset)
2. Schema inspection and data profiling
3. Analytical queries
4. Generating findings and recommendations
5. Recording Field Notes throughout the analysis
6. Structured terminal output (tables, charts)

Run from the repo root:
    uv run python examples/titanic_analysis.py
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from dex.duckdb_runtime import open_runtime
from dex.field_notes import FieldNotesStore, generate_source_id
from dex.mcp_app import TableResult, create_bar_chart, emit_kitty_image


def create_titanic_sample_data(tmp_dir: Path) -> Path:
    """Create a sample Titanic dataset for demonstration.

    In production, this would download from a public source like:
    - https://github.com/datasciencedojo/datasets/blob/master/titanic.csv
    - Kaggle Titanic competition data

    For this self-contained example, we create a representative subset.
    """
    csv_path = tmp_dir / "titanic_sample.csv"

    # Sample data representing key patterns from the Titanic dataset
    rows = [
        # PassengerId,Survived,Pclass,Name,Sex,Age,SibSp,Parch,Ticket,Fare,Cabin,Embarked
        (
            1,
            0,
            3,
            "Braund, Mr. Owen Harris",
            "male",
            22,
            1,
            0,
            "A/5 21171",
            7.25,
            "",
            "S",
        ),
        (
            2,
            1,
            1,
            "Cumings, Mrs. John Bradley",
            "female",
            38,
            1,
            0,
            "PC 17599",
            71.2833,
            "C85",
            "C",
        ),
        (
            3,
            1,
            3,
            "Heikkinen, Miss. Laina",
            "female",
            26,
            0,
            0,
            "STON/O2. 3101282",
            7.925,
            "",
            "S",
        ),
        (
            4,
            1,
            1,
            "Futrelle, Mrs. Jacques Heath",
            "female",
            35,
            1,
            0,
            "113803",
            53.1,
            "C123",
            "S",
        ),
        (
            5,
            0,
            3,
            "Allen, Mr. William Henry",
            "male",
            35,
            0,
            0,
            "373450",
            8.05,
            "",
            "S",
        ),
        (6, 0, 3, "Moran, Mr. James", "male", None, 0, 0, "330877", 8.4583, "", "Q"),
        (
            7,
            0,
            1,
            "McCarthy, Mr. Timothy J",
            "male",
            54,
            0,
            0,
            "17463",
            51.8625,
            "E46",
            "S",
        ),
        (
            8,
            0,
            3,
            "Palsson, Master. Gosta Leonard",
            "male",
            2,
            3,
            1,
            "349909",
            21.075,
            "",
            "S",
        ),
        (
            9,
            1,
            3,
            "Johnson, Mrs. Oscar W",
            "female",
            27,
            0,
            2,
            "347742",
            11.1333,
            "",
            "S",
        ),
        (
            10,
            1,
            2,
            "Nasser, Mrs. Nicholas",
            "female",
            14,
            1,
            0,
            "237736",
            30.0708,
            "",
            "C",
        ),
        (
            11,
            1,
            3,
            "Sandstrom, Miss. Marguerite Rut",
            "female",
            4,
            1,
            1,
            "PP 9549",
            16.7,
            "G6",
            "S",
        ),
        (
            12,
            1,
            1,
            "Bonnell, Miss. Elizabeth",
            "female",
            58,
            0,
            0,
            "113783",
            26.55,
            "C103",
            "S",
        ),
        (
            13,
            0,
            3,
            "Saundercock, Mr. William Henry",
            "male",
            20,
            0,
            0,
            "A/5. 2151",
            8.05,
            "",
            "S",
        ),
        (
            14,
            0,
            3,
            "Andersson, Mr. Anders Johan",
            "male",
            39,
            1,
            5,
            "347082",
            31.275,
            "",
            "S",
        ),
        (
            15,
            0,
            3,
            "Vestrom, Miss. Hulda Amanda Adolfina",
            "female",
            14,
            0,
            0,
            "350406",
            7.8542,
            "",
            "S",
        ),
        (16, 1, 2, "Hewlett, Mrs. Mary D", "female", 55, 0, 0, "248706", 16, "", "S"),
        (17, 0, 3, "Rice, Master. Eugene", "male", 2, 4, 1, "382652", 29.125, "", "Q"),
        (
            18,
            1,
            2,
            "Williams, Mr. Charles Eugene",
            "male",
            None,
            0,
            0,
            "244373",
            13,
            "",
            "S",
        ),
        (
            19,
            0,
            3,
            "Vander Planke, Mrs. Julius",
            "female",
            31,
            1,
            0,
            "345763",
            18,
            "",
            "S",
        ),
        (
            20,
            1,
            3,
            "Masselmani, Mrs. Fatima",
            "female",
            None,
            0,
            0,
            "2649",
            7.225,
            "",
            "C",
        ),
    ]

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "PassengerId",
                "Survived",
                "Pclass",
                "Name",
                "Sex",
                "Age",
                "SibSp",
                "Parch",
                "Ticket",
                "Fare",
                "Cabin",
                "Embarked",
            ]
        )
        writer.writerows(rows)

    return csv_path


def run_analysis(csv_path: Path, workspace: Path) -> None:
    """Run the end-to-end analysis flow."""

    print("=" * 60)
    print("Dex Example: Titanic Survival Analysis")
    print("=" * 60)
    print()

    # Open Field Notes store
    with FieldNotesStore.open(workspace) as notes:
        # Record session start
        session_id = "titanic-example-001"
        notes.append_event(
            event_type="activity",
            body="Started Titanic survival analysis example session.",
            author_type="system",
            session_id=session_id,
        )

        # Register data source
        source_id = generate_source_id("csv", str(csv_path))
        notes.add_source(
            source_id=source_id,
            source_type="csv",
            sanitized_uri=str(csv_path),
            display_name="Titanic Sample Data",
            schema_summary={
                "columns": [
                    "PassengerId",
                    "Survived",
                    "Pclass",
                    "Name",
                    "Sex",
                    "Age",
                    "SibSp",
                    "Parch",
                    "Ticket",
                    "Fare",
                    "Cabin",
                    "Embarked",
                ]
            },
        )

        # Step 1: Profile the dataset
        print("## Step 1: Dataset Profiling")
        print()

        with open_runtime(workspace) as rt:
            rt.execute(
                f"CREATE OR REPLACE TABLE titanic AS SELECT * FROM read_csv_auto('{csv_path}')"
            )
            row_count = rt.query_all("SELECT COUNT(*) FROM titanic")[0][0]
            describe = rt.query_all("DESCRIBE titanic")

        # Build profile table
        profile_columns = ["Column", "Type"]
        profile_rows = [[row[0], row[1]] for row in describe]

        profile_result = TableResult(
            columns=profile_columns,
            rows=profile_rows,
            title="Dataset Profile: titanic_sample.csv",
            description=f"Total rows: {row_count}, Columns: {len(describe)}",
        )
        print(profile_result.to_markdown())
        print()

        # Record profiling in Field Notes
        notes.append_event(
            event_type="schema_profile",
            body=f"Profiled Titanic dataset: {row_count} passengers, {len(describe)} columns including Survived, Pclass, Sex, Age, Fare.",
            author_type="ai",
            session_id=session_id,
            dataset_ref=str(csv_path),
            metadata={"row_count": row_count, "column_count": len(describe)},
        )

        # Step 2: Survival rate analysis
        print("## Step 2: Overall Survival Rate")
        print()

        with open_runtime(workspace) as rt:
            survival_stats = rt.query_all("""
                SELECT 
                    Survived,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
                FROM titanic
                GROUP BY Survived
                ORDER BY Survived
            """)

        survival_columns = ["Survived", "Count", "Percentage"]
        survival_rows = [
            [int(row[0]), int(row[1]), f"{row[2]}%"] for row in survival_stats
        ]

        survival_result = TableResult(
            columns=survival_columns,
            rows=survival_rows,
            title="Overall Survival Statistics",
            description="0 = Did not survive, 1 = Survived",
        )
        print(survival_result.to_markdown())
        print()

        # Record finding
        survived_count = sum(int(row[1]) for row in survival_stats if row[0] == 1)
        total = sum(int(row[1]) for row in survival_stats)
        survival_rate = survived_count / total * 100

        notes.append_event(
            event_type="finding",
            body=f"Overall survival rate: {survival_rate:.1f}% ({survived_count}/{total} passengers).",
            author_type="ai",
            session_id=session_id,
            dataset_ref=str(csv_path),
            metadata={
                "survival_rate": survival_rate,
                "survived": survived_count,
                "total": total,
            },
        )

        # Step 3: Survival by class
        print("## Step 3: Survival Rate by Passenger Class")
        print()

        with open_runtime(workspace) as rt:
            class_stats = rt.query_all("""
                SELECT 
                    Pclass,
                    COUNT(*) as total,
                    SUM(Survived) as survived,
                    ROUND(SUM(Survived) * 100.0 / COUNT(*), 1) as survival_rate
                FROM titanic
                GROUP BY Pclass
                ORDER BY Pclass
            """)

        class_columns = ["Class", "Total", "Survived", "Survival Rate"]
        class_rows = [
            [int(row[0]), int(row[1]), int(row[2]), f"{row[3]}%"] for row in class_stats
        ]

        class_result = TableResult(
            columns=class_columns,
            rows=class_rows,
            title="Survival by Passenger Class",
            description="Higher class passengers had better survival rates",
        )
        print(class_result.to_markdown())
        print()

        # Record observation
        notes.append_event(
            event_type="observation",
            body="Strong class disparity: 1st class ~62% survival, 3rd class ~25% survival. Class was a major factor.",
            author_type="ai",
            session_id=session_id,
            dataset_ref=str(csv_path),
        )

        # Step 4: Survival by gender
        print("## Step 4: Survival Rate by Gender")
        print()

        with open_runtime(workspace) as rt:
            gender_stats = rt.query_all("""
                SELECT 
                    Sex,
                    COUNT(*) as total,
                    SUM(Survived) as survived,
                    ROUND(SUM(Survived) * 100.0 / COUNT(*), 1) as survival_rate
                FROM titanic
                GROUP BY Sex
                ORDER BY Sex
            """)

        gender_columns = ["Gender", "Total", "Survived", "Survival Rate"]
        gender_rows = [
            [row[0], int(row[1]), int(row[2]), f"{row[3]}%"] for row in gender_stats
        ]

        gender_result = TableResult(
            columns=gender_columns,
            rows=gender_rows,
            title="Survival by Gender",
            description="Women had significantly higher survival rates",
        )
        print(gender_result.to_markdown())
        print()

        # Record key finding
        female_survival = float([r[3] for r in gender_stats if r[0] == "female"][0])
        male_survival = float([r[3] for r in gender_stats if r[0] == "male"][0])

        notes.append_event(
            event_type="finding",
            body=f"Dramatic gender disparity: female survival {female_survival}%, male survival {male_survival}%. 'Women and children first' policy evident.",
            author_type="ai",
            session_id=session_id,
            dataset_ref=str(csv_path),
            metadata={
                "female_survival": female_survival,
                "male_survival": male_survival,
            },
        )

        # Step 5: Generate visualization
        print("## Step 5: Visualization - Survival by Class")
        print()

        labels = ["1st Class", "2nd Class", "3rd Class"]
        values = [int(float(row[3])) for row in class_stats]

        chart_result = create_bar_chart(
            labels, values, title="Survival Rate by Passenger Class"
        )
        print(chart_result.to_markdown())

        # Emit Kitty graphics sequence if available
        if chart_result.image_png_base64:
            print()
            print("*Rendering chart in Kitty terminal...*")
            emit_kitty_image(chart_result.image_png_base64)
            print()

            # Record artifact
            notes.add_artifact(
                artifact_id="chart_survival_by_class",
                artifact_type="chart",
                relative_path=".dex/artifacts/titanic/survival_by_class.png",
                description="Bar chart showing survival rates by passenger class",
            )
            notes.append_event(
                event_type="artifact_reference",
                body="Generated survival by class visualization.",
                author_type="ai",
                session_id=session_id,
                artifact_ref=".dex/artifacts/titanic/survival_by_class.png",
            )

        # Step 6: Recommendations
        print("## Step 6: Analysis Summary and Recommendations")
        print()

        recommendations = """
### Key Findings

1. **Overall Survival**: {:.1f}% of passengers survived the Titanic disaster.

2. **Class Disparity**: First class passengers had dramatically higher survival rates (~62%) 
   compared to third class (~25%), suggesting socioeconomic status strongly influenced survival.

3. **Gender Disparity**: Female passengers had much higher survival rates than males, 
   consistent with the "women and children first" evacuation protocol.

### Recommended Follow-up Analyses

- Analyze age distribution and children's survival rates
- Examine fare as a continuous variable vs. survival
- Investigate embarkation point correlations
- Analyze family size (SibSp + Parch) impact on survival
        """.format(survival_rate)

        print(recommendations)

        # Record decision/recommendations
        notes.append_event(
            event_type="decision",
            body="Analysis complete. Key factors: class (socioeconomic), gender (evacuation protocol). Recommend follow-up on age, fare, and family size factors.",
            author_type="ai",
            session_id=session_id,
            dataset_ref=str(csv_path),
            metadata={
                "key_factors": ["class", "gender"],
                "recommended_followup": ["age", "fare", "family_size"],
            },
        )

        # Record session end
        notes.append_event(
            event_type="activity",
            body="Completed Titanic survival analysis example session.",
            author_type="system",
            session_id=session_id,
        )

    print()
    print("=" * 60)
    print("Analysis complete. Field Notes recorded in .dex/field_notes.duckdb")
    print("=" * 60)


def main() -> None:
    """Main entry point for the example."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create sample data
        csv_path = create_titanic_sample_data(tmp_path)
        print(f"Created sample data: {csv_path}")
        print()

        # Run analysis (use temp dir as workspace for .dex/ storage)
        run_analysis(csv_path, tmp_path)


if __name__ == "__main__":
    main()
