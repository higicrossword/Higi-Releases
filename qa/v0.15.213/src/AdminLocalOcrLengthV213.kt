package com.example.hebrewcrossword

/** Read-only, best-effort local OCR evidence for administrator comparisons.
 *
 * Tesseract's Hebrew text order is an observation, not a photograph-verified
 * enumeration. A candidate is returned only when a single multi-part tuple is
 * attributable to an in-order numbered clue and its sum matches the grid.
 * Never use this as an automatic correction or Canonical authorization.
 */
object AdminLocalOcrLengthV213 {
    data class Key(val direction: String, val number: Int)
    private val marker = Regex("(?<![0-9])([0-9]{1,3})\\s*\\.")
    private val enumeration = Regex("\\(\\s*([0-9]{1,2}(?:\\s*[,;.]\\s*[0-9]{1,2}){1,5})\\s*\\)")

    fun extract(
        original: String,
        expectedHorizontal: Map<Int, Int>,
        expectedVertical: Map<Int, Int>
    ): Map<Key, List<Int>> {
        val text=original.replace(Regex("[\\u200e\\u200f\\u202a-\\u202e\\u2066-\\u2069]"), " ")
            .replace(Regex("\\s+"), " ").trim()
        val h=Regex("מאוזן\\s*:").find(text) ?: return emptyMap()
        val v=Regex("מאונך\\s*:").find(text, h.range.last+1) ?: return emptyMap()
        if(v.range.first<=h.range.last)return emptyMap()
        val output=linkedMapOf<Key,List<Int>>()
        fun scan(section:String,direction:String,expected:Map<Int,Int>) {
            val labels=marker.findAll(section).mapNotNull { m ->
                val n=m.groupValues[1].toIntOrNull() ?: return@mapNotNull null
                if(n !in expected)return@mapNotNull null
                n to m
            }.toList()
            if(labels.map{it.first}.distinct().size!=labels.size ||
                labels.zipWithNext().any{(a,b)->a.first>=b.first})return
            labels.forEachIndexed { i,(number,m) ->
                val end=labels.getOrNull(i+1)?.second?.range?.first ?: section.length
                val clue=section.substring(m.range.last+1,end)
                val matches=enumeration.findAll(clue).toList()
                if(matches.size!=1)return@forEachIndexed
                val parts=Regex("[0-9]{1,2}").findAll(matches.single().groupValues[1])
                    .map{it.value.toInt()}.toList()
                val sum=parts.sum()
                val hasExplicitReference=("מאוזן" in clue || "מאונך" in clue) &&
                    Regex("[0-9]{1,3}\\s*(מאוזן|מאונך)").containsMatchIn(clue)
                val validTotal=sum==expected[number] ||
                    (hasExplicitReference && sum>(expected[number]?:0))
                if(parts.size in 2..6 && parts.all{it in 1..99} && validTotal)
                    output[Key(direction,number)]=parts
            }
        }
        scan(text.substring(h.range.last+1,v.range.first),"across",expectedHorizontal)
        scan(text.substring(v.range.last+1),"down",expectedVertical)
        return output
    }
}
