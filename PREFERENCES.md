Those are critical architectural questions. As your project manager and architect, here are my recommendations based on our goal: **to quickly build a robust, professional-looking prototype for the university to evaluate.**

---
### 1. Dashboard: Pure Django or React/JS Front-end?

**Recommendation:** We should continue with the **Hybrid Approach** we've already started.

* **Pure Django Templates (Too Static):** This would mean every single click (like moving a slider) requires a full page reload. It's too slow and feels outdated for the level of interactivity we need.
* **Full React/JS Front-end (Too Complex):** This would require you to build two separate applications: a Django REST Framework API (the "backend") and a complete React application (the "front-end"). This is a significant increase in complexity, and for an internship prototype, it's not the most efficient use of time.
* **The Hybrid Approach (Our Current Method - The Best Choice):** We use Django templates to render the main page and then "sprinkle" in interactive JavaScript (like D3.js and `fetch`) to handle real-time features like the sliders and dropdowns. This gives us the best of both worlds: fast development and a modern, interactive feel.

---
### 2. File Storage: Local Disk or Cloud (S3)?

**Recommendation:** Use **Local Disk Storage** for now.

* **Why:** For a prototype running on your local machine, this is the simplest and fastest solution. It requires zero setup. We can build the file upload logic using Django's standard `FileField`, and it will "just work" on your computer.
* **The Future:** The best part about using Django's file handling is that we can easily "swap" the storage backend later. If the university approves the prototype for production, we can install a package like `django-storages` and, with a few changes in `settings.py`, make it save files to an S3 bucket without having to rewrite our models or views.

---
### 3. Design: Bootstrap, Tailwind, or Custom?

**Recommendation:** Stick with **Bootstrap 5**.

* **Why:** We are already using it successfully via a CDN link.
    * **Speed:** It gives us professional-looking components (cards, forms, dropdowns, grids) right out of the box.
    * **No Setup:** We don't need to install any `npm` packages or configure a complex CSS build step, which would be required for Tailwind.
    * **Academic Feel:** Bootstrap's clean, standard design is perfect for an academic tool. We can focus on functionality, not on custom styling.

These choices prioritize **rapid, robust development** and let you focus on learning the core Django logic, which is the main goal of your internship.