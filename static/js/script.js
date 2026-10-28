document.addEventListener("DOMContentLoaded", function () {
    console.log("FixIt JavaScript loaded successfully.");

    const reportForm = document.querySelector("#reportForm");

    if (reportForm) {
        reportForm.addEventListener("submit", function (event) {
            

            const category = document.querySelector("#category").value;
            const location = document.querySelector("#location").value.trim();
            const description = document.querySelector("#description").value.trim();

            if (!category || !location || !description) {
                alert("Please fill in all required fields.");
                return;
            }

            alert("Issue details validated successfully!");
        });
    }
});