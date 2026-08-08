document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".file-picker input[type='file']").forEach((input) => {
        const picker = input.closest(".file-picker");
        const status = picker ? picker.querySelector(".file-picker-text") : null;
        if (!status) {
            return;
        }

        input.addEventListener("change", () => {
            const files = Array.from(input.files || []);
            if (files.length === 0) {
                status.textContent = "Nenhum arquivo selecionado";
                picker.classList.remove("has-files");
                return;
            }

            picker.classList.add("has-files");
            status.textContent = files.length === 1 ? files[0].name : `${files.length} arquivos selecionados`;
        });
    });

    document.querySelectorAll("[data-toggle-details]").forEach((button) => {
        button.addEventListener("click", () => {
            const card = button.closest(".queue-item");
            const details = card ? card.querySelector(".queue-card-disclosure") : null;
            if (!details) {
                return;
            }

            details.open = !details.open;
            button.classList.toggle("is-open", details.open);
            button.textContent = details.open ? "Fechar" : "Abrir";
            button.setAttribute("aria-expanded", details.open ? "true" : "false");
        });
    });
});
