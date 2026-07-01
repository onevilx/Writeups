<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>1337 | The Piscine Diaries</title>

    <style>
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;700&family=Montserrat:wght@400;600;700;900&display=swap');

        :root {
            --treize-cyan: #00babc;
            --treize-dark: #0f1011;
            --treize-gray: #1e1f22;
            --treize-light-gray: #2a2c30;
            --treize-text: #e1e1e1;
        }

        body {
            font-family: 'Montserrat', sans-serif;
            background-color: var(--treize-dark);
            color: var(--treize-text);
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }

        header {
            background: var(--treize-gray);
            border-bottom: 2px solid var(--treize-cyan);
            padding: 20px 0;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
        }

        .logo {
            font-size: 2.5rem;
            font-weight: 900;
            color: white;
            font-family: 'Fira Code', monospace;
            margin: 0;
        }

        .logo span {
            color: var(--treize-cyan);
        }

        .subtitle {
            color: #888;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        .container {
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
        }

        .post {
            background: var(--treize-gray);
            border-radius: 8px;
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }

        .post-title {
            color: white;
            font-size: 1.8rem;
            margin-top: 0;
            margin-bottom: 10px;
        }

        .post-meta {
            color: var(--treize-cyan);
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
            margin-bottom: 20px;
        }

        .post-content {
            color: #a0aec0;
        }

        .comment-section {
            background: var(--treize-gray);
            border-radius: 8px;
            padding: 30px;
            margin-top: 50px;
            border-top: 4px solid var(--treize-cyan);
        }

        .comment-section h2 {
            color: white;
            margin-top: 0;
        }

        textarea {
            width: 100%;
            height: 120px;
            padding: 15px;
            background: var(--treize-light-gray);
            border: 1px solid #444;
            border-radius: 4px;
            color: white;
            font-family: 'Fira Code', monospace;
            box-sizing: border-box;
            outline: none;
            resize: vertical;
            transition: 0.3s;
            margin-bottom: 15px;
        }

        textarea:focus {
            border-color: var(--treize-cyan);
            box-shadow: 0 0 10px rgba(0, 186, 188, 0.2);
        }

        button {
            background: transparent;
            color: var(--treize-cyan);
            border: 1px solid var(--treize-cyan);
            padding: 12px 25px;
            border-radius: 4px;
            font-weight: bold;
            font-family: 'Fira Code', monospace;
            text-transform: uppercase;
            cursor: pointer;
            transition: 0.3s;
        }

        button:hover {
            background: var(--treize-cyan);
            color: var(--treize-dark);
            box-shadow: 0 0 15px rgba(0, 186, 188, 0.4);
        }

        .preview-box {
            margin-bottom: 25px;
            padding: 20px;
            background: rgba(0, 186, 188, 0.1);
            border: 1px solid rgba(0, 186, 188, 0.3);
            border-left: 4px solid var(--treize-cyan);
            border-radius: 4px;
            font-family: 'Montserrat', sans-serif;
            color: #ffffff;
            word-break: break-all;
            white-space: pre-wrap;
            font-size: 1.05rem;
            box-shadow: inset 0 0 15px rgba(0, 0, 0, 0.5);
        }

        .preview-box h3 {
            color: var(--treize-cyan);
            margin-top: 0;
            font-size: 1.1rem;
        }

        .error-box {
            margin-bottom: 25px;
            padding: 20px;
            background: rgba(255, 76, 76, 0.05);
            border: 1px solid rgba(255, 76, 76, 0.2);
            border-left: 4px solid #ff4c4c;
            border-radius: 4px;
            color: #ff8888;
            font-family: 'Fira Code', monospace;
        }

        .hint-text {
            font-size: 0.8rem;
            color: #555;
            margin-top: 10px;
            font-family: 'Fira Code', monospace;
        }
    </style>
</head>

<body>
    <header>
        <h1 class="logo">13<span>37</span></h1>
        <div class="subtitle">The Piscine Diaries</div>
    </header>

    <div class="container">

        <div class="post">
            <h2 class="post-title">Surviving Shell00</h2>
            <div class="post-meta">Posted by bocal_staff | Aug 16, 2024</div>
            <div class="post-content">
                <p>Welcome to the first day of the rest of your life. The Piscine is designed to break you down and
                    build you back up. Don't worry if `find` and `tar` are giving you nightmares. By the end of the
                    week, the terminal will be your best friend.</p>
                <p>Remember: RTFM is the only true answer.</p>
            </div>
        </div>

        <div class="post">
            <h2 class="post-title">Why the Norminette is actually your friend</h2>
            <div class="post-meta">Posted by the_norm | July 21, 2025</div>
            <div class="post-content">
                <p>We know you hate it when you get a `Norme Error`. But strict coding standards are what separate the
                    good coders from the great ones. 25 lines per function? 5 variables max? It forces you to think
                    modularly. Embrace the pain.</p>
            </div>
        </div>

        <div class="comment-section">
            <h2>Leave a Comment</h2>

            {if $preview}
            {if $error}
            <div class="error-box">
                [SYSTEM_ALERT] <br><br>
                {$preview}
            </div>
            {else}
            <div class="preview-box">
                {$preview nofilter}
            </div>
            {/if}
            {/if}

            <form action="/" method="GET" id="commentForm">
                <input type="hidden" name="action" value="preview">
                <textarea name="text" id="commentBox" placeholder="Write your thoughts here..." required></textarea>
                <button type="submit">Preview Comment</button>
            </form>
        </div>

    </div>

    {literal}
    <script>
        document.getElementById('commentBox').addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                document.getElementById('commentForm').submit();
            }
        });
    </script>
    {/literal}
</body>

</html>
