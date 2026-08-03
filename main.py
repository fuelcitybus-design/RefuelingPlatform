今天
global active_tabs.txt

純文字

It got stuck at loading after using the save image function, this randomly occurs, no error messages, usually occurs if more than one image is uploaded at the same time, but I can see that it was able to upload the photos by look at kudu storage
I dug into your save_images function, and the “random stuck at loading” behavior you’re seeing is consistent with how Gradio handles multiple outputs when backend calls don’t return cleanly. The fact that uploads succeed in Kudu storage but the UI hangs means the frontend is waiting for a proper string response that sometimes never arrives. Here are the key culprits in your code:

🔎 Likely Causes
Multiple concurrent uploads:
When more than one image is uploaded, each requests.put call is synchronous. If one stalls or returns unexpected text, the loop continues but Gradio may not finalize the response until all branches complete.

Return type mismatch:
You correctly join messages into a string at the end, but inside the loop you sometimes append error messages without short‑circuiting. If an exception occurs before the final return "\n".join(messages), Gradio can hang.

Backend “session not found”:
Your debug log shows Response {status_code}: {response.text}. If the backend returns HTML or plain text instead of JSON, the .json() parsing earlier can throw, leaving the UI spinning.

Global state mutation:
filepath, tank_choices, and active_tabs are mutated globally. If multiple users or multiple calls overlap, the state can get inconsistent and stall the UI.

✅ Fixes to Try
Always finalize with a string:
Ensure every branch ends with a string return. For example:

python
return "\n".join(messages) if messages else "完成但沒有訊息"
This prevents Gradio from waiting indefinitely.

Add per‑upload timeouts:

python
response = requests.put(filepath, data=buffer.getvalue(), auth=auth, timeout=5)
This avoids hanging if one upload stalls.

Skip phantom images:
You already check if img is None or not hasattr(img, "size"). Add a guard for corrupted inputs:

python
if not getattr(img, "size", None):
    continue
Log backend responses clearly:
Instead of just response.text, print the first 200 characters. That way you’ll see if “session not found” is coming from a redirect or auth failure.

Short‑circuit on fatal errors:
If folder creation fails or connection error occurs, return immediately with a string rather than continuing the loop.

🛠 Debugging Tip
Try uploading three images at once and watch the console logs. If one requests.put returns “session not found,” the UI will hang until that call completes. Adding timeouts and ensuring the function always returns a string will stop the frontend from spinning.

Would you like me to draft a standalone test script (outside Gradio) that uploads multiple images to your Kudu storage in parallel? That way you can confirm whether the “session not found” issue is backend‑side or purely Gradio’s synchronous blocking.

global active_tabs.txt

純文字

Some problem again after the suggested modifications
I see why the problem persists — the modifications helped with corrupted inputs, but the random “stuck loading” is still happening because Gradio is waiting for a clean return while your synchronous upload loop occasionally blocks. The uploads succeed (you see them in Kudu), but the frontend doesn’t get a finalized response string in time.

Here are the next refinements you should apply:

🔧 Key Adjustments
Force non‑blocking uploads  
Wrap each requests.put in a try/except with a timeout and ensure you always append a message, even if the call fails. Right now, if requests.put hangs longer than 5 seconds, Gradio waits indefinitely.

python
try:
    response = requests.put(filepath, data=buffer.getvalue(), auth=auth, timeout=5)
    status = response.status_code
    if status not in [200, 201]:
        messages.append(f"❌{tab_name} save failed (status {status}).")
    else:
        saved_paths.append(tab_name)
        detected_tabs_exist.append(tab_name)
except requests.Timeout:
    messages.append(f"❌{tab_name} upload timed out.")
except Exception as e:
    messages.append(f"❌{tab_name} upload error: {str(e)}")
Return immediately after loop  
Don’t let Gradio hang waiting for completion. After the loop, finalize with:

python
return "\n".join(messages) or "完成但沒有訊息"
This guarantees a string even if something unexpected happens.

Avoid global mutation mid‑call  
filepath, tank_choices, and active_tabs are global. If multiple users or multiple uploads overlap, state corruption can occur. Use locals inside save_images and only update globals in dropdown/toggle functions.

Parallelize uploads (optional)  
If backend latency is the culprit, use concurrent.futures.ThreadPoolExecutor to upload images in parallel. That way, one slow upload won’t block the entire Gradio response.

🧪 Debugging Strategy
Add print("Loop finished, returning messages") right before the final return.
If you don’t see this log, it means the loop is stuck on a blocking request.

Test with 2–3 images simultaneously. If one times out, you should now see "upload timed out" in the textbox instead of endless loading.

If the backend sometimes returns HTML (like “session not found”), capture the first 200 chars of response.text and append it to messages. That way you’ll see the failure reason in Gradio instead of silence.

🚀 Next Step
Would you like me to draft a parallel upload version of save_images using ThreadPoolExecutor? That would eliminate the “one slow request blocks all” problem and make Gradio return promptly even if one image fails.

2026-08-03T07:04:40.2562091Z File "/tmp/8def12d15bd53e6/main.py", line 270 2026-08-03T07:04:40.2562136Z if len(saved_paths)>0: 2026-08-03T07:04:40.2562158Z SyntaxError: expected 'except' or 'finally' block
That traceback is telling you Python hit an if statement but was still inside a try: block that hadn’t been closed with an except or finally. In other words, the indentation or block structure is off.

Looking at your snippet:

python
try:
    # upload loop...
    for i, img in enumerate(images):
        ...
        try:
            response = requests.put(filepath, ...)
            ...
        except Exception as e:
            messages.append(f"❌{tab_name} upload error: {str(e)}")

    # --- Completion message ---
    if len(saved_paths)>0:   # <-- SyntaxError here
        ...
The error means Python thinks that if len(saved_paths)>0: is still inside the inner try: but outside of any except/finally. That happens if the except block above is mis‑indented or missing. For example:

python
        try:
            response = requests.put(filepath, ...)
            ...
        # MISSING except here
    # Python expects except/finally before continuing
✅ How to fix
Make sure every try: has a matching except or finally at the same indentation level. For example:

python
for i, img in enumerate(images):
    if img is None or not hasattr(img, "size"):
        continue
    try:
        response = requests.put(filepath, data=buffer.getvalue(), auth=auth, timeout=5)
        if response.status_code not in [200, 201]:
            messages.append(f"❌{tab_name} save failed (status {response.status_code}).")
        else:
            saved_paths.append(tab_name)
            detected_tabs_exist.append(tab_name)
    except Exception as e:
        messages.append(f"❌{tab_name} upload error: {str(e)}")
# <-- now we’re safely back outside the loop and try/except
if len(saved_paths) > 0:
    ...
🔎 Checklist
Align except with its try: (same indentation).

Don’t leave a try: without an except or finally.

After the loop, you can safely run if len(saved_paths)>0:.

If you want, I can rewrite your save_images function with properly nested try/except blocks and guaranteed string returns, so you won’t hit this syntax error again. Would you like me to draft that corrected version?

It sometimes suddenly session is not found
The “session not found” issue you’re seeing isn’t a Python syntax error — it’s coming from the backend (your Kudu storage / API). That message usually means the upload request is hitting a stale or invalid session context. Since you can see the files in storage, the upload itself works, but Gradio gets stuck because the backend returns an error page instead of a clean JSON or 200/201 response.

Here are the most common causes and fixes:

🔎 Why “session not found” happens
Expired authentication: If auth is a temporary token or cookie, it may expire between requests. Multiple uploads in one call can trigger this if the backend revalidates each PUT.

Trailing slash in URLs: Some Kudu endpoints treat /path/ differently from /path. If the folder URL or file URL is slightly off, the backend may respond with “session not found.”

Concurrency: Uploading several images back‑to‑back can cause race conditions if the backend expects sequential folder creation.

Backend returning HTML: If the response is an error page, your code still tries to parse JSON or treat it as success, leaving Gradio waiting.

✅ What to change in your code
Refresh or re‑use auth correctly  
Make sure auth is a persistent (username, password) tuple or valid token, not a one‑time session cookie.

Normalize URLs  
Remove trailing slashes when building base_url and add them only when needed:

python
base_url = f"{ROOT_FOLDER}/{today}/{prefix}"
filepath = f"{base_url}/{filename}"
Add explicit timeout and error handling

python
try:
    response = requests.put(filepath, data=buffer.getvalue(), auth=auth, timeout=5)
    if response.status_code not in [200, 201]:
        messages.append(f"❌{tab_name} save failed ({response.status_code}): {response.text[:200]}")
    else:
        saved_paths.append(tab_name)
except requests.Timeout:
    messages.append(f"❌{tab_name} upload timed out.")
except Exception as e:
    messages.append(f"❌{tab_name} upload error: {str(e)}")
Always finalize with a string  
Even if one upload fails, return "\n".join(messages) so Gradio doesn’t hang.

Log backend responses  
Print the first 200 characters of response.text so you can see if “session not found” is coming from a redirect, expired token, or malformed URL.

🧪 Debugging step
Run a standalone test script outside Gradio that uploads two images in parallel to the same folder. If you see “session not found” there, it’s definitely backend auth/session handling. If not, the issue is Gradio’s synchronous blocking.

Would you like me to draft that standalone test uploader (just a short Python script using requests.put) so you can confirm whether the “session not found” is backend‑side or Gradio‑side? That will pinpoint whether you need to fix authentication or restructure the Gradio function.

it writes error 404, but all images were uploaded or ignored successfully
Got it — the 404 plus “session not found” is a backend quirk, not a Python bug. What’s happening is:

The PUT requests to Kudu succeed (files are uploaded or skipped correctly).

But when you later GET the folder URL, Kudu sometimes returns a 404 or “session not found” page instead of JSON.

Your code then tries to parse that response, logs the error, and Gradio shows the failure message even though the files are already there.

🔎 Why this happens
Folder URL mismatch: Kudu’s VFS API expects /api/vfs/site/... style paths. If you add or omit a trailing slash, you can get 404 even though the file exists.

Auth/session: If you’re using a cookie or temporary token, it may expire mid‑loop. Basic auth (username/password) is more stable.

Race condition: You create the folder with PUT, then immediately GET it. Sometimes the folder metadata isn’t available yet, so the GET returns 404 even though the files are written.

✅ How to stabilize
Normalize URLs  
Always build base_url without a trailing slash, then append filenames:

python
base_url = f"{ROOT_FOLDER}/{today}/{prefix}"
filepath = f"{base_url}/{filename}"
Skip GET if not needed  
Instead of checking folder contents before every upload, trust your own saved_paths list. That way you don’t depend on Kudu’s JSON response.

Graceful fallback on 404  
Wrap the GET in:

python
try:
    baser = requests.get(base_url, auth=auth, timeout=5)
    if baser.status_code == 200:
        items = baser.json()
        ...
    else:
        items = []
except Exception as e:
    items = []
This way, a 404 doesn’t block the rest of the function.

Delay before GET (optional)  
If you really need to read folder contents, add a short sleep:

python
time.sleep(0.5)
before the GET, so Kudu has time to update metadata.

🧪 Debugging tip
Print the exact URL that returns 404. If it’s the folder path (ending with /), try removing the slash. If it’s the file path, check whether you’re double‑adding slashes (...//filename.jpg).

Would you like me to draft a leaner version of save_images that avoids the folder GET entirely and just reports based on what was uploaded in this call? That would eliminate the random 404s while still giving users clear “uploaded/skipped” messages.

try:
            baser = requests.get(base_url, auth=auth, timeout=5)
            if baser.status_code in [200, 201]:
                try:
                    items = baser.json()
                except ValueError:
                    items = []
                existing_files = [item["name"] for item in items if item.get("mime") != "inode/directory"]
                for f in existing_files:
                    name, ext = os.path.splitext(f)
                    detected_tabs_exist.append(name)
                    if "油車前" in name.lower():
                        detected_tabs_exist.append("油車前")
                    if "油車後" in name.lower():
                        detected_tabs_exist.append("油車後")
            else:
                response = requests.put(base_url, auth=auth, timeout=5)
                if response.status_code not in [200, 201]:
                    return "❌Folder creation failed."
        except Exception as e:
            return f"❌Connection error: {str(e)}" help me modify this
The block you shared is fine in principle, but the way it’s written means you’re tightly coupling folder existence checks with JSON parsing. That’s why you sometimes see 404 or “session not found” even though the uploads succeed. You can make this more robust by:

Treating 200 only as a valid “folder exists” response.

Falling back gracefully on 404/other codes without trying to parse JSON.

Ensuring you always initialize items and existing_files so later code doesn’t break.

Logging the response text for debugging, but not letting it block the rest of the function.

Here’s a safer rewrite:

python
try:
    baser = requests.get(base_url, auth=auth, timeout=5)
    if baser.status_code == 200:
        try:
            items = baser.json()
        except ValueError:
            items = []
        existing_files = [
            item.get("name")
            for item in items
            if item.get("mime") != "inode/directory"
        ]
        for f in existing_files:
            name, ext = os.path.splitext(f)
            detected_tabs_exist.append(name)
            if "油車前" in name.lower():
                detected_tabs_exist.append("油車前")
            if "油車後" in name.lower():
                detected_tabs_exist.append("油車後")
    elif baser.status_code == 404:
        # Folder not found, try to create it
        response = requests.put(base_url, auth=auth, timeout=5)
        if response.status_code not in [200, 201]:
            return "❌Folder creation failed."
        existing_files = []
    else:
        # Unexpected status, but don’t block uploads
        print(f"Warning: GET {base_url} returned {baser.status_code} {baser.text[:200]}")
        existing_files = []
except Exception as e:
    print("Connection error:", e)
    existing_files = []
🔑 Improvements
404 handled explicitly: instead of treating it as a fatal error, you attempt folder creation.

Other codes logged but ignored: avoids hanging the function.

Always initializes existing_files: prevents later code from crashing.

Debug logging: shows you what the backend actually returned.

This way, even if Kudu returns 404 or “session not found,” your function continues and uploads work without Gradio hanging.

Would you like me to also show you how to skip the folder GET entirely and just rely on your own saved_paths list? That would eliminate these random 404s altogether.

+ Exception Group Traceback (most recent call last):
2026-08-03T07:28:14.4837961Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/uvicorn/protocols/http/h11_impl.py", line 415, in run_asgi
2026-08-03T07:28:14.4837981Z   |     result = await app(  # type: ignore[func-returns-value]
2026-08-03T07:28:14.4837997Z   |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-03T07:28:14.4838016Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/uvicorn/middleware/proxy_headers.py", line 63, in __call__
2026-08-03T07:28:14.4838031Z   |     return await self.app(scope, receive, send)
2026-08-03T07:28:14.4838046Z   |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-03T07:28:14.4838064Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/fastapi/applications.py", line 1054, in __call__
2026-08-03T07:28:14.4838082Z   |     await super().__call__(scope, receive, send)
2026-08-03T07:28:14.4838101Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/applications.py", line 113, in __call__
2026-08-03T07:28:14.4838117Z   |     await self.middleware_stack(scope, receive, send)
2026-08-03T07:28:14.4838189Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/middleware/errors.py", line 187, in __call__
2026-08-03T07:28:14.4838203Z   |     raise exc
2026-08-03T07:28:14.4838221Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/middleware/errors.py", line 165, in __call__
2026-08-03T07:28:14.4838236Z   |     await self.app(scope, receive, _send)
2026-08-03T07:28:14.4838253Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/middleware/exceptions.py", line 62, in __call__
2026-08-03T07:28:14.4838269Z   |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
2026-08-03T07:28:14.4838287Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/_exception_handler.py", line 62, in wrapped_app
2026-08-03T07:28:14.48383Z   |     raise exc
2026-08-03T07:28:14.4838317Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/_exception_handler.py", line 51, in wrapped_app
2026-08-03T07:28:14.4838332Z   |     await app(scope, receive, sender)
2026-08-03T07:28:14.4838349Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/routing.py", line 715, in __call__
2026-08-03T07:28:14.4838364Z   |     await self.middleware_stack(scope, receive, send)
2026-08-03T07:28:14.4838399Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/routing.py", line 735, in app
2026-08-03T07:28:14.4838414Z   |     await route.handle(scope, receive, send)
2026-08-03T07:28:14.4838431Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/routing.py", line 460, in handle
2026-08-03T07:28:14.4838445Z   |     await self.app(scope, receive, send)
2026-08-03T07:28:14.4838463Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/fastapi/applications.py", line 1054, in __call__
2026-08-03T07:28:14.4838478Z   |     await super().__call__(scope, receive, send)
2026-08-03T07:28:14.4838495Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/applications.py", line 113, in __call__
2026-08-03T07:28:14.483851Z   |     await self.middleware_stack(scope, receive, send)
2026-08-03T07:28:14.4838527Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/middleware/errors.py", line 187, in __call__
2026-08-03T07:28:14.4838574Z   |     raise exc
2026-08-03T07:28:14.4838592Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/middleware/errors.py", line 165, in __call__
2026-08-03T07:28:14.4838607Z   |     await self.app(scope, receive, _send)
2026-08-03T07:28:14.4838623Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/gradio/brotli_middleware.py", line 74, in __call__
2026-08-03T07:28:14.4838637Z   |     return await self.app(scope, receive, send)
2026-08-03T07:28:14.4838651Z   |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-08-03T07:28:14.4838667Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/gradio/route_utils.py", line 882, in __call__
2026-08-03T07:28:14.4838681Z   |     await self.app(scope, receive, send)
2026-08-03T07:28:14.4838698Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/middleware/exceptions.py", line 62, in __call__
2026-08-03T07:28:14.4838713Z   |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
2026-08-03T07:28:14.4838731Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/_exception_handler.py", line 62, in wrapped_app
2026-08-03T07:28:14.4838743Z   |     raise exc
2026-08-03T07:28:14.4838781Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/_exception_handler.py", line 51, in wrapped_app
2026-08-03T07:28:14.4838795Z   |     await app(scope, receive, sender)
2026-08-03T07:28:14.4838811Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/routing.py", line 715, in __call__
2026-08-03T07:28:14.4838826Z   |     await self.middleware_stack(scope, receive, send)
2026-08-03T07:28:14.5049507Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/routing.py", line 735, in app
2026-08-03T07:28:14.5049735Z   |     await route.handle(scope, receive, send)
2026-08-03T07:28:14.5049761Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/routing.py", line 288, in handle
2026-08-03T07:28:14.5049775Z   |     await self.app(scope, receive, send)
2026-08-03T07:28:14.5049794Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/routing.py", line 76, in app
2026-08-03T07:28:14.5049817Z   |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
2026-08-03T07:28:14.5049836Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/_exception_handler.py", line 62, in wrapped_app
2026-08-03T07:28:14.5049848Z   |     raise exc
2026-08-03T07:28:14.5049922Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/_exception_handler.py", line 51, in wrapped_app
2026-08-03T07:28:14.5049937Z   |     await app(scope, receive, sender)
2026-08-03T07:28:14.5049955Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/routing.py", line 74, in app
2026-08-03T07:28:14.5049968Z   |     await response(scope, receive, send)
2026-08-03T07:28:14.5049985Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/responses.py", line 252, in __call__
2026-08-03T07:28:14.505Z   |     async with anyio.create_task_group() as task_group:
2026-08-03T07:28:14.5050019Z   |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/anyio/_backends/_asyncio.py", line 815, in __aexit__
2026-08-03T07:28:14.5050033Z   |     raise BaseExceptionGroup(
2026-08-03T07:28:14.5050049Z   | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
2026-08-03T07:28:14.5050063Z   +-+---------------- 1 ----------------
2026-08-03T07:28:14.5050077Z     | Traceback (most recent call last):
2026-08-03T07:28:14.5050094Z     |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/anyio/_core/_tasks.py", line 275, in _run_coro
2026-08-03T07:28:14.5050139Z     |     retval = await self._coro
2026-08-03T07:28:14.5050152Z     |              ^^^^^^^^^^^^^^^^
2026-08-03T07:28:14.5050169Z     |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/responses.py", line 255, in wrap
2026-08-03T07:28:14.5050182Z     |     await func()
2026-08-03T07:28:14.50502Z     |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/starlette/responses.py", line 244, in stream_response
2026-08-03T07:28:14.5050214Z     |     async for chunk in self.body_iterator:
2026-08-03T07:28:14.5050232Z     |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/gradio/routes.py", line 1529, in sse_stream
2026-08-03T07:28:14.5050244Z     |     raise e
2026-08-03T07:28:14.505026Z     |   File "/tmp/8def13030c493f6/antenv/lib/python3.11/site-packages/gradio/routes.py", line 1453, in sse_stream
2026-08-03T07:28:14.5050274Z     |     raise HTTPException(
2026-08-03T07:28:14.5050289Z     | fastapi.exceptions.HTTPException: 404: Not Found
2026-08-03T07:28:14.5050319Z     +------------------------------------ The source of all errors
Thanks for sharing the full traceback — this confirms the root cause. The fastapi.exceptions.HTTPException: 404: Not Found inside Gradio’s sse_stream is the source of all errors. That’s why you see the “session not found” behavior even though uploads succeed.

🔎 What’s happening
Gradio uses Server-Sent Events (SSE) to stream status back to the browser.

Your save_images function completes, but when Gradio tries to stream the final response, it looks up a job/event ID that no longer exists.

That lookup fails → FastAPI raises a 404 → Starlette/Gradio try to wrap it → but the response stream has already started, so you get the messy exception group.

The frontend hangs because the SSE stream was interrupted.

✅ How to fix
Upgrade dependencies  
Make sure you’re on the latest compatible versions:

bash
pip install "fastapi>=0.115.2" "starlette>=0.40.0" "gradio>=5.0.0"
Older versions have known SSE bugs.

Always return a clean string  
Your function already does return "\n".join(messages). Keep that, but ensure no branch exits early without returning a string.

Avoid double exception bubbling  
Add a custom handler so FastAPI doesn’t try to re‑wrap the 404:

python
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 404 and "sse_stream" in str(exc.detail).lower():
        return PlainTextResponse("Stream job not found", status_code=404)
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)
Check Gradio queue setup  
If you’re using app.queue(), confirm jobs aren’t being cleared too quickly. Add logging for job IDs when they’re created and requested.

Test with a minimal app  
Strip out the folder GET/PUT logic and run a barebones Gradio save_images that just returns "OK". If the error disappears, the issue is in the backend call timing. If it persists, it’s Gradio’s SSE layer.

🧪 Practical Debugging
Add print("Returning messages:", messages) right before the final return.

If you see that log but still get 404 in SSE, the bug is in Gradio’s job queue, not your function.

If you don’t see the log, your function is stuck in a blocking request.

👉 In short: the uploads succeed, but the SSE job ID goes missing before Gradio streams the response. Updating FastAPI/Starlette/Gradio and adding a graceful handler for 404 inside sse_stream usually resolves this.

Would you like me to draft a minimal FastAPI + Gradio queue example you can run to confirm whether the error is in your app logic or purely in the dependency versions?

requirement list
Since you asked about the requirements list, let’s clarify what that means in the context of your Gradio app. In Python projects, a requirements.txt file is used to declare all the external libraries your code depends on, so that anyone can install them with pip install -r requirements.txt.

Looking at your code, here are the packages you’ll need to include:

gradio → for the UI framework (gr.Blocks, gr.Image, gr.Dropdown, etc.)

requests → for HTTP calls to Kudu storage (requests.get, requests.put)

Pillow → for image handling (img.resize, img.save)

fastapi → because Gradio mounts into FastAPI (gr.mount_gradio_app)

uvicorn → to serve the FastAPI app

anyio → required by FastAPI/Starlette for async task groups

starlette → underlying ASGI framework used by FastAPI

brotli → used by Gradio’s middleware for compression

Optional but recommended:

python-dotenv if you want to manage secrets like auth or ROOT_FOLDER via environment variables.

typing-extensions for compatibility with newer type hints.

Example requirements.txt
text
gradio>=5.0.0
requests>=2.31.0
Pillow>=10.0.0
fastapi>=0.115.2
uvicorn>=0.30.0
anyio>=4.0.0
starlette>=0.40.0
brotli>=1.1.0
python-dotenv>=1.0.0
typing-extensions>=4.12.0
This ensures your app runs without the 404/SSE errors caused by mismatched dependency versions.

Do you want me to also pin exact versions (instead of >=) so that your deployment environment is fully reproducible? That can help avoid the random “session not found” errors you’ve been seeing.

@app.exception_handler(HTTPException)
2026-08-03T07:36:14.3492148Z                            ^^^^^^^^^^^^^
2026-08-03T07:36:14.3492162Z NameError: name 'HTTPException' is not defined
2026-08-03T07:36:14.3570676Z name 'HTTPException' is not defined
The NameError: name 'HTTPException' is not defined is happening because you didn’t import HTTPException before using it in your @app.exception_handler. FastAPI provides this class, so you need to bring it into scope.

Here’s the corrected snippet:

python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Handle SSE 404 gracefully
    if exc.status_code == 404:
        return PlainTextResponse("Stream job not found", status_code=404)
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)
🔑 Key points
Import HTTPException from fastapi.

Also import Request and PlainTextResponse since you’re using them.

This handler intercepts FastAPI’s 404 errors (including those from Gradio’s SSE stream) and returns a plain text response instead of crashing with an exception group.

If you want to keep things lean, you can also just catch all exceptions:

python
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return PlainTextResponse(f"Error: {str(exc)}", status_code=500)
