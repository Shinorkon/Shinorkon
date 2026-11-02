package com.shinorkon.zimyo

import android.app.Activity
import android.os.Bundle
import android.text.InputType
import android.widget.*

class MainActivity : Activity() {
    override fun onCreate(b: Bundle?) {
        super.onCreate(b)
        val p = getSharedPreferences("z", MODE_PRIVATE)
        val l = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48, 96, 48, 48) }
        val u = EditText(this).apply { hint = "Email / employee code"; setText(p.getString("u", "")) }
        val pw = EditText(this).apply {
            hint = "Password"; setText(p.getString("p", ""))
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        val s = Button(this).apply {
            text = "Save"
            setOnClickListener { Zimyo.save(this@MainActivity, u.text.toString().trim(), pw.text.toString())
                Toast.makeText(context, "Saved. Now add the Zimyo Clock widget to your home screen.", Toast.LENGTH_LONG).show() }
        }
        l.addView(TextView(this).apply { text = "Zimyo login (stored only on this phone)" })
        l.addView(u); l.addView(pw); l.addView(s)
        setContentView(l)
    }
}
