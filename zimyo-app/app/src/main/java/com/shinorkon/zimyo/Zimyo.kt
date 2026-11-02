package com.shinorkon.zimyo

import android.content.Context
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

object Zimyo {
    private const val BASE = "https://www.zimyo.work/apiv2"

    fun save(ctx: Context, user: String, pass: String) =
        ctx.getSharedPreferences("z", Context.MODE_PRIVATE).edit().putString("u", user).putString("p", pass).apply()

    private fun post(url: String, body: JSONObject, token: String?): JSONObject {
        val c = URL(url).openConnection() as HttpURLConnection
        c.requestMethod = "POST"; c.connectTimeout = 15000; c.readTimeout = 15000
        c.setRequestProperty("Content-Type", "application/json")
        c.setRequestProperty("Accept", "application/json")
        if (token == null) { c.setRequestProperty("app_name", "account"); c.setRequestProperty("app_lang", "en") }
        else c.setRequestProperty("token", token)
        c.doOutput = true
        c.outputStream.use { it.write(body.toString().toByteArray()) }
        val s = (if (c.responseCode < 400) c.inputStream else c.errorStream).bufferedReader().readText()
        return JSONObject(s)
    }

    /** action = "in" or "out". Returns a short status message. */
    fun punch(ctx: Context, action: String): String = try {
        val p = ctx.getSharedPreferences("z", Context.MODE_PRIVATE)
        val user = p.getString("u", "") ?: ""; val pass = p.getString("p", "") ?: ""
        if (user.isEmpty()) return "Open the app and save your login"
        val login = post("$BASE/login_api", JSONObject().put("username", user).put("password", pass), null)
        val data = login.optJSONObject("data")
        val token = data?.optString("token").orEmpty()
        val emp = (data?.optJSONObject("auth_user_detail") ?: data?.optJSONObject("auth"))?.opt("user_emp_id")?.toString().orEmpty()
        if (token.isEmpty() || emp.isEmpty()) {
            if (data?.optBoolean("show_otp_input") == true) "Login needs OTP (unsupported)"
            else "Login failed: " + login.optString("message", "unknown")
        } else {
            val st = post("$BASE/auth/hrms/check-clock-in-out-status", JSONObject().put("EMP_ID", emp), token)
            val att = st.optJSONObject("data")?.optJSONObject("attendance")
            val isIn = att?.optString("IN_OUT_STATUS") == "In"
            val date = att?.optString("DATE").orEmpty()
            if (action == "in" && isIn) "Already clocked in"
            else if (action == "out" && !isIn) "Not clocked in"
            else {
                val r = post("$BASE/auth/hrms/clock-in-out",
                    JSONObject().put("EMP_ID", emp).put("SOURCE", "Web").put("DATE", date).put("PLACE", ""), token)
                if (!r.optBoolean("error", true)) "Clocked $action" else "Failed: " + r.optString("message")
            }
        }
    } catch (e: Exception) { "Error: ${e.message}" }
}
