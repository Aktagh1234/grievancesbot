const loginTab = document.getElementById("login-tab");
const signupTab = document.getElementById("signup-tab");
const formTitle = document.getElementById("form-title");
const formContent = document.getElementById("form-content");

loginTab.addEventListener("click", () => {
  loginTab.classList.add("active");
  signupTab.classList.remove("active");
  formTitle.textContent = "LOGIN FORM";

  formContent.innerHTML = `
    <div class="input-wrapper">
      <span class="icon">📧</span>
      <input type="email" id="login-email" placeholder="Enter your email" />
    </div>
    <div class="input-wrapper">
      <span class="icon">🔐</span>
      <input type="password" id="login-password" placeholder="Enter your password" />
    </div>
    <button id="login-btn">Sign In</button>
  `;

  document.getElementById("login-btn").addEventListener("click", async () => {
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    try {
      const response = await fetch("http://127.0.0.1:5000/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();
      alert(data.message || data.error);
    } catch (error) {
      alert("Something went wrong. Please try again.");
    }
  });
});

signupTab.addEventListener("click", () => {
  signupTab.classList.add("active");
  loginTab.classList.remove("active");
  formTitle.textContent = "SIGNUP FORM";

  formContent.innerHTML = `
    <div class="input-wrapper">
      <span class="icon">📧</span>
      <input type="email" id="signup-email" placeholder="Enter your email" />
    </div>
    <div class="input-wrapper">
      <span class="icon">🔒</span>
      <input type="password" id="signup-password" placeholder="Create password" />
    </div>
    <div class="input-wrapper">
      <span class="icon">✅</span>
      <input type="password" id="confirm-password" placeholder="Confirm password" />
    </div>
    <button id="signup-btn">Sign Up</button>
  `;

  document.getElementById("signup-btn").addEventListener("click", async () => {
    const email = document.getElementById("signup-email").value;
    const password = document.getElementById("signup-password").value;
    const confirmPassword = document.getElementById("confirm-password").value;

    if (password !== confirmPassword) {
      alert("Passwords do not match!");
      return;
    }

    try {
      const response = await fetch("http://127.0.0.1:5000/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();
      alert(data.message || data.error);
    } catch (error) {
      alert("Something went wrong. Please try again.");
    }
  });
});

// Load login form by default
loginTab.click();
