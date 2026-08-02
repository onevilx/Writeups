# Intigriti LeakyJar Challenge — CSRF to Steal Admin's Secret Recipe

> **Challenge:** [Intigriti LeakyJar CTF Challenge](https://leakyjar.intigriti.io)  
> **Endpoint:** `https://leakyjar.intigriti.io/share`  
> **Vulnerability Category:** Cross-Site Request Forgery (CSRF) & Cookie Security Misconfiguration  
> **Severity:** Medium (Tier 2 Web Exploitation)  
> **Flag:** `INTIGRITI{019ef404-1e44-7748-bdcf-ca7b12dbfee0}`

---

## 1. Executive Summary & Challenge Premise

In the **Intigriti LeakyJar** competition, participants were confronted with a secure enterprise document vault engineered for professional chefs to manage and protect proprietary recipes. Our mission: manipulate an automated administrative evaluation bot (the "Master Baker") into leaking its encrypted private recipe vault—which protected the competition capture flag—directly to our unprivileged guest account.

The application is vulnerable to Cross-Site Request Forgery (CSRF) on the `/share` endpoint. Because there are no anti-CSRF tokens protecting form submissions, and the session cookie is explicitly configured with the `SameSite=None` attribute, cross-origin requests can be fully authenticated. By hosting a malicious webpage that automatically submits a POST request to `/share` targeting our attacker username, we can force the Master Baker bot to share their private vault with us upon visiting our payload URL.

---

## 2. Deep Dive into Cookie Security: SameSite Fallouts

To understand why this vulnerability exists, we must evaluate the precise architectural mechanics of modern HTTP browser cookie attribution.

When a user logs into a web portal, the authentication engine issues a permanent session token preserved inside a browser storage cookie. When the user subsequently navigates around the web application, the browser automatically attaches that cookie to every outgoing request heading toward the origin domain.

### The SameSite Security Configuration

To protect users from malicious external websites attempting to generate fraudulent unauthorized commands (CSRF), standard browser architecture enforces the **`SameSite`** cookie instruction. Modern browsers typically default to `SameSite=Lax`, which blocks cross-site POST requests from attaching session cookies.

However, during our authentication flow inspection against LeakyJar's login gateway, we intercepted the explicit server response header setting our persistent session token:

```http
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: session_id=s%3A2984910283401923.xK89012398jalkd98; Path=/; Secure; HttpOnly; SameSite=None
```

The server developer explicitly declared **`SameSite=None`**. By declaring `SameSite=None` without implementing rigorous Anti-CSRF token synchronization validation, the browser is instructed to *always* attach the session cookie across all external cross-site requests and form posts, leaving the application entirely exposed to CSRF exploitation.

---

## 3. Exploit Architecture & Payload Design

With the vulnerability confirmed, we engineered an automated Cross-Origin exploit payload designed to force the headless Chromium Master Baker support bot into transferring collaborative viewing authorizations directly to our possession.

### Autonomous Exploit Payload (`exploit.html`)

To ensure our attack executes silently and instantaneously when visited by the headless browser, we construct an automated, self-submitting HTML Form:

```html
<!DOCTYPE html>
<html>
<body>
    <form id="csrf" action="https://leakyjar.intigriti.io/share" method="POST">
        <!-- Target our attacker username to receive the shared vault -->
        <input type="hidden" name="username" value="onevilx">
    </form>
    
    <!-- Execute instant zero-click automated payload transmission -->
    <script>
        document.getElementById('csrf').submit();
    </script>
</body>
</html>
```

When the Master Baker visits this page, their browser automatically attaches their `SameSite=None` administrative session cookie to the POST request, authorizing the sharing action.

---

## 4. Exploitation Walkthrough (Steps to Solve)

1. **Account Registration:** Registered an attacker account (`onevilx`) on the challenge platform.
2. **Payload Creation:** Created the malicious HTML page (`exploit.html`) containing an auto-submitting POST form directed at `https://leakyjar.intigriti.io/share`, with the `username` parameter set to my own username.
3. **Payload Hosting:** Hosted the malicious HTML page on a publicly accessible server (using `python3 -m http.server` and a tunneling service like `localhost.run`).
4. **Target Execution:** Submitted the public URL of the exploit page to the Master Baker via the "Report a recipe" endpoint (`/submit`).
5. **CSRF Trigger:** Waited for the admin bot to visit the URL, which triggered the CSRF attack and shared the admin's vault with my account.
6. **Flag Retrieval:** Navigated to my "My recipe box" (`/vault`) page. Found "admin's recipe box" under the "Shared with you" section, clicked "View", and retrieved the flag from the secret recipe.

---

## 5. Security Impact

An attacker can force any logged-in user (including administrative accounts) to share their private recipe box with the attacker without their knowledge or consent. This leads to a complete breach of confidentiality for the user's private data, allowing the attacker to read all recipes and secret notes stored in the victim's vault.

---

## 6. Remediation & Recommended Solutions

Eliminating Cross-Site Request Forgery vulnerabilities demands enforcing robust, defense-in-depth authorization verification across all state-changing API endpoints.

### Fix 1: Reconfigure Cookie Attributes (Fail-Secure)
Change the `SameSite` attribute on the session cookie from `None` to `Lax` or `Strict`. This will prevent the browser from sending the session cookie along with cross-site POST requests, neutralizing the CSRF attack vector natively at the browser level.

### Fix 2: Implement Anti-CSRF Tokens
All state-changing endpoints (like `POST /share`) should require a unique, unpredictable anti-CSRF synchronizer token that is validated on the server side prior to execution.
