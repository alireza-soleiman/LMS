# Project Notes: LMS Workshop Prototypes

This document outlines the current state of the custom Django (Prototype A) service, detailing the implemented workshops, dependencies, and testing information.

## 1. Implemented Workshops

The core logic resides in the `workshops` app. We have implemented the two main components of the "Evaluation Methods and Decision Making Approaches" course (WS2 from the provided materials).

### Workshop 1: Stakeholder Analysis

* **Description:** This tool allows students to perform a complete stakeholder analysis. They can add stakeholders, assign numerical scores (0-100) for **Power** and **Interest**, and classify each stakeholder by **Level**, **Typology**, and **Resource**.
* **Key Features:**
    * An interactive table for real-time editing of all stakeholder attributes.
    * Slider controls for adjusting Power and Interest values.
    * Tag-style dropdowns for classifying categories, which are saved asynchronously via `fetch`.
    * A real-time **D3.js Power/Interest Matrix** that automatically updates when slider values are changed.
* **Code Location:**
    * **App:** `workshops`
    * **Models:** `Stakeholder` in `workshops/models.py`
    * **Views:**
        * `stakeholder_list`: Renders the main page and form.
        * `stakeholder_data`: Provides JSON data for the D3.js chart.
        * `update_stakeholder_details`: API endpoint for handling real-time table edits (sliders, dropdowns).
        * `download_stakeholders_csv`: Generates the CSV download of the table.
        * (All in `workshops/views.py`)
    * **Template:** `workshops/templates/workshops/stakeholder_list.html`

### Workshop 2: Problem Tree Analysis

* **Description:** This tool allows students to build a hierarchical problem tree based on the **Core Problem, Effects, and Causes** model.
* **Key Features:**
    * Students can add nodes, define their type (Core, Cause, Effect), and link them to a parent node (e.g., a sub-cause to a cause, or a cause to a core problem).
    * The system uses the **Graphviz** Python library to generate a static SVG diagram on the backend, ensuring a correct hierarchical layout (Effects above Core, Causes below).
    * The diagram correctly renders multi-level nested causes.
    * Arrows point in the logical direction of causation (Causes -> Core, Core -> Effects).
    * A "Manage Problems" list allows students to **delete** any node.
    * A color picker allows students to set a **custom color** for any node.
* **Code Location:**
    * **App:** `workshops`
    * **Models:** `Problem` in `workshops/models.py`
    * **Views:**
        * `problem_tree_view`: Renders the page, form, and the Graphviz SVG.
        * `delete_problem`: Handles the deletion of a node.
        * `download_problem_tree_png`: Generates the PNG download.
        * (All in `workshops/views.py`)
    * **Template:** `workshops/templates/workshops/problem_tree_graphviz.html`

## 2. Special Third-Party Integrations

This project has several key dependencies:

* **Graphviz (Critical):** This is a **server-side dependency**. The `graphviz` Python library requires the separate **Graphviz software** (specifically the `dot` executable) to be installed on the host system and available in the system's `PATH` variable to render the problem tree diagrams.
* **D3.js:** Used client-side (via CDN) to render the interactive Stakeholder Matrix.
* **Bootstrap 5:** Used client-side (via CDN) for all page styling and components (cards, forms, dropdowns).
* **html2canvas:** Used client-side (via CDN) to generate the PNG downloads for the stakeholder matrix and table.

*No cloud services (e.g., S3, Google Drive) or Moodle LTI integrations have been implemented at this stage.*

## 3. How Students Upload/Download Results

Students "upload" data by filling out the forms on each page and using the interactive table.

#### Stakeholder Analysis
* **Download Matrix:** "Download Matrix as PNG" button (Client-side, `html2canvas`).
* **Download Table (Visual):** "Download Table as PNG" button (Client-side, `html2canvas`, hides sliders).
* **Download Table (Data):** "Download Table as CSV" button (Server-side, `download_stakeholders_csv` view).

#### Problem Tree Analysis
* **Download Tree:** "Download Tree as PNG" button (Server-side, `download_problem_tree_png` view).

## 4. Sample Test User

Formal student accounts and group authentication are not yet implemented. All testing can be performed using the Django Admin superuser.

* **URL:** `/admin/`
* **Username:** `admin`
* **Password:** Sh.36903690