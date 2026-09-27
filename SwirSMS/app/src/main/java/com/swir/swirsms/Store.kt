package com.swir.swirsms

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

class LocalPrefs(context: Context) {
    private val p = context.getSharedPreferences("standalone_v3", Context.MODE_PRIVATE)
    var reports: Boolean get() = p.getBoolean("reports", true); set(v) { p.edit().putBoolean("reports", v).apply() }
    var lock: Boolean get() = p.getBoolean("lock", false); set(v) { p.edit().putBoolean("lock", v).apply() }
    var lang: String get() = p.getString("lang", "system")!!; set(v) { p.edit().putString("lang", v).apply() }
    var draft: String get() = p.getString("draft", "")!!; set(v) { p.edit().putString("draft", v).apply() }
    var draftPeople: List<Recipient> get() = decodePeople(p.getString("draft_people", "[]")!!); set(v) { p.edit().putString("draft_people", encodePeople(v)).apply() }
    var selectedSim: Int get() = p.getInt("sim", -1); set(v) { p.edit().putInt("sim", v).apply() }
}
fun encodePeople(people: List<Recipient>): String = JSONArray().apply { people.forEach { put(JSONObject().put("name", it.name).put("number", it.number)) } }.toString()
fun decodePeople(value: String): List<Recipient> = runCatching { val a = JSONArray(value); (0 until a.length()).map { val o = a.getJSONObject(it); Recipient(o.getString("name"), o.getString("number")) } }.getOrDefault(emptyList())

class SmsDb private constructor(context: Context) : SQLiteOpenHelper(context, "standalone.db", null, 1) {
    val revision = MutableStateFlow(0L)
    companion object {
        @Volatile private var instance: SmsDb? = null
        fun get(context: Context): SmsDb = instance ?: synchronized(this) { instance ?: SmsDb(context.applicationContext).also { instance = it } }
    }
    override fun onConfigure(db: SQLiteDatabase) { db.setForeignKeyConstraintsEnabled(true) }
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE messages(id TEXT PRIMARY KEY, created INTEGER NOT NULL, due INTEGER NOT NULL, name TEXT NOT NULL, number TEXT NOT NULL, body TEXT NOT NULL, sim INTEGER NOT NULL, sim_label TEXT NOT NULL, reports INTEGER NOT NULL, state TEXT NOT NULL, parts INTEGER NOT NULL DEFAULT 0, detail TEXT NOT NULL DEFAULT '', token TEXT NOT NULL, updated INTEGER NOT NULL)")
        db.execSQL("CREATE INDEX pending_messages ON messages(state,due)")
        db.execSQL("CREATE TABLE parts(message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE, part INTEGER NOT NULL, sent INTEGER NOT NULL DEFAULT 0, delivered INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(message_id,part))")
        db.execSQL("CREATE TABLE saved(id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, people TEXT NOT NULL)")
    }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) { error("Unsupported database migration") }
    private fun change() { revision.update { it + 1 } }
    private inline fun <T> tx(block: (SQLiteDatabase) -> T): T {
        val db = writableDatabase; db.beginTransaction()
        return try { val result = block(db); db.setTransactionSuccessful(); result } finally { db.endTransaction(); change() }
    }
    private fun Cursor.message() = Message(getString(0),getLong(1),getLong(2),getString(3),getString(4),getString(5),getInt(6),getString(7),getInt(8)==1,getString(9),getInt(10),getString(11),getString(12))
    private val columns = "id,created,due,name,number,body,sim,sim_label,reports,state,parts,detail,token"
    fun getMessage(id: String): Message? = readableDatabase.rawQuery("SELECT $columns FROM messages WHERE id=?", arrayOf(id)).use { if (it.moveToFirst()) it.message() else null }
    // Never hide a queued or uncertain message behind the completed-history limit.
    fun messages(): List<Message> = readableDatabase.rawQuery("SELECT $columns FROM messages WHERE state IN ('QUEUED','SENDING','UNKNOWN') OR id IN (SELECT id FROM messages WHERE state NOT IN ('QUEUED','SENDING','UNKNOWN') ORDER BY created DESC LIMIT 300) ORDER BY created DESC", null).use { c -> buildList { while(c.moveToNext()) add(c.message()) } }
    fun pending(): List<Message> = readableDatabase.rawQuery("SELECT $columns FROM messages WHERE state='QUEUED' ORDER BY due", null).use { c -> buildList { while(c.moveToNext()) add(c.message()) } }
    fun addBatch(people: List<Recipient>, body: String, sim: SimChoice, due: Long, reports: Boolean): List<String> {
        require(people.isNotEmpty() && people.size <= 20 && body.isNotBlank() && body.length <= 1530)
        require(people.all { PhoneRules.normalize(it.number) == it.number } && people.distinctBy { it.number }.size == people.size)
        require(sim.id >= 0)
        return tx { db -> people.map { p ->
            val id = UUID.randomUUID().toString()
            db.insertOrThrow("messages", null, ContentValues().apply {
                put("id", id); put("created", System.currentTimeMillis()); put("due", due); put("name",p.name); put("number",p.number); put("body",body)
                put("sim",sim.id); put("sim_label",sim.label); put("reports",if(reports) 1 else 0); put("state","QUEUED"); put("token",UUID.randomUUID().toString()); put("updated",System.currentTimeMillis())
            }); id
        } }
    }
    fun claim(id: String, now: Long): Message? = tx { db ->
        val updated = db.update("messages", ContentValues().apply { put("state","SENDING"); put("updated",now) }, "id=? AND state='QUEUED' AND due<=?", arrayOf(id, now.toString()))
        if(updated==1) getMessage(id) else null
    }
    fun prepareParts(id: String, count: Int) = tx { db ->
        require(count in 1..10)
        db.update("messages", ContentValues().apply { put("parts",count) }, "id=?",arrayOf(id))
        repeat(count) { i -> db.insertOrThrow("parts", null, ContentValues().apply { put("message_id",id); put("part",i) }) }
    }
    fun mark(id: String, state: String, detail: String) = tx { db ->
        db.update("messages",ContentValues().apply { put("state",state); put("detail",detail.take(300)); put("updated",System.currentTimeMillis()) },"id=? AND state NOT IN ('CANCELLED','DELIVERED')",arrayOf(id))
    }
    fun cancel(id: String): Boolean = tx { db -> db.update("messages",ContentValues().apply { put("state","CANCELLED") },"id=? AND state='QUEUED'",arrayOf(id))==1 }
    fun record(id: String, token: String, part: Int, delivered: Boolean, value: Int, error: String = "") = tx { db ->
        val msg = getMessage(id) ?: return@tx
        if(msg.token != token || part !in 0 until msg.parts || value !in listOf(-1,1)) return@tx
        if(msg.state in listOf("CANCELLED","EXPIRED")) return@tx
        val field = if(delivered) "delivered" else "sent"
        db.update("parts",ContentValues().apply { put(field,value) },"message_id=? AND part=? AND $field=0",arrayOf(id,part.toString()))
        val counts = db.rawQuery("SELECT SUM(sent=1),SUM(sent=-1),SUM(delivered=1),SUM(delivered=-1) FROM parts WHERE message_id=?",arrayOf(id)).use { it.moveToFirst(); IntArray(4) { i -> it.getInt(i) } }
        val state = ResultRules.state(msg.parts,counts[0],counts[1],counts[2],counts[3])
        db.update("messages",ContentValues().apply { put("state",state); put("updated",System.currentTimeMillis()); if(error.isNotBlank()) put("detail",error.take(300)) },"id=?",arrayOf(id))
    }
    fun markUncertain() = tx { db ->
        db.update("messages",ContentValues().apply { put("state","UNKNOWN"); put("detail","NO_CALLBACK") },"state='SENDING' AND updated<?",arrayOf((System.currentTimeMillis()-300_000).toString()))
    }
    fun clearFinished() = tx { db -> db.delete("messages","state NOT IN ('QUEUED','SENDING','UNKNOWN')",null) }
    fun delete(id: String) = tx { db -> db.delete("messages","id=? AND state NOT IN ('QUEUED','SENDING','UNKNOWN')",arrayOf(id)) }
    fun saved(): List<SavedItem> = readableDatabase.rawQuery("SELECT id,kind,title,body,people FROM saved ORDER BY title COLLATE NOCASE",null).use { c -> buildList { while(c.moveToNext()) add(SavedItem(c.getString(0),c.getString(1),c.getString(2),c.getString(3),decodePeople(c.getString(4)))) } }
    fun save(item: SavedItem) = tx { db ->
        require(item.title.isNotBlank() && item.title.length<=80 && item.body.length<=1530 && item.people.size<=20)
        db.insertWithOnConflict("saved",null,ContentValues().apply { put("id",item.id); put("kind",item.kind); put("title",item.title); put("body",item.body); put("people",encodePeople(item.people)) },SQLiteDatabase.CONFLICT_REPLACE)
    }
    fun deleteSaved(id: String) = tx { db -> db.delete("saved","id=?",arrayOf(id)) }
}
