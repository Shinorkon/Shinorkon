package com.shinorkon.zimyo

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class ZimyoWidget : AppWidgetProvider() {
    override fun onUpdate(ctx: Context, mgr: AppWidgetManager, ids: IntArray) = render(ctx, mgr, "Ready")

    override fun onReceive(ctx: Context, intent: Intent) {
        super.onReceive(ctx, intent)
        val a = intent.action
        if (a == "zimyo.IN" || a == "zimyo.OUT") {
            val pending = goAsync()
            val mgr = AppWidgetManager.getInstance(ctx)
            render(ctx, mgr, "Working...")
            Thread {
                val msg = Zimyo.punch(ctx, if (a == "zimyo.IN") "in" else "out")
                render(ctx, mgr, msg + " " + SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date()))
                pending.finish()
            }.start()
        }
    }

    private fun render(ctx: Context, mgr: AppWidgetManager, status: String) {
        val v = RemoteViews(ctx.packageName, R.layout.widget)
        v.setOnClickPendingIntent(R.id.btn_in, pi(ctx, "zimyo.IN"))
        v.setOnClickPendingIntent(R.id.btn_out, pi(ctx, "zimyo.OUT"))
        v.setTextViewText(R.id.status, status)
        mgr.updateAppWidget(ComponentName(ctx, ZimyoWidget::class.java), v)
    }

    private fun pi(ctx: Context, action: String) = PendingIntent.getBroadcast(
        ctx, action.hashCode(), Intent(ctx, ZimyoWidget::class.java).setAction(action),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
}
