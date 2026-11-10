package com.example.hebrewcrossword

/** Stable OCR layout profiles. Selection only affects administrator DRY review.
 * Never select a profile merely because a source image happens to have similar X coordinates.
 */
object OcrSeriesProfilesV197 {
    data class Profile(val id:String, val revision:Int=1, val mondayBoundaryReview:Boolean=false)
    val GENERIC=Profile("GENERIC")
    val TARTEY=Profile("TARTEY_DEKEL")
    val HAFUCH=Profile("HAFUCH_DEKEL")
    val MONDAY=Profile("YEDIOTH_MONDAY_DEKEL",mondayBoundaryReview=true)
    val WEDNESDAY=Profile("YEDIOTH_WEDNESDAY_DEKEL")
    val MAARIV=Profile("MAARIV_ODED_ROZEN")
    val MAKOR=Profile("MAKOR_RISHON")
    val LAISHA=Profile("LAISHA_DEKEL")
    val OTHERS=mapOf(
        "TZAFNAT_PAANEACH" to Profile("TZAFNAT_PAANEACH"),
        "ISRAEL_HAYOM_BIRMAN" to Profile("ISRAEL_HAYOM_BIRMAN"),
        "BARUCH_LIOR" to Profile("BARUCH_LIOR"),
        "GUEST_AVISHAI" to Profile("GUEST_AVISHAI"))
    private val stable=mapOf(TARTEY.id to TARTEY,HAFUCH.id to HAFUCH,
        MONDAY.id to MONDAY,WEDNESDAY.id to WEDNESDAY,MAARIV.id to MAARIV,
        MAKOR.id to MAKOR,LAISHA.id to LAISHA)+OTHERS

    fun resolve(title:String,sourceKey:String):Profile {
        val prefix=sourceKey.substringBefore(':')
        if(prefix in stable)return stable.getValue(prefix)
        val text=title.substringBefore('—').substringBefore('·').trim()
        // Fail closed on ambiguous titles, in particular 'דקל בנו' without day/series.
        val id=when {
            "תרתי משמע" in text -> TARTEY.id
            "הפוך על הפוך" in text -> HAFUCH.id
            "דקל בנו שני" in text -> MONDAY.id
            "דקל בנו רביעי" in text -> WEDNESDAY.id
            "מקור ראשון" in text -> MAKOR.id
            "מעריב" in text && "אורח" !in text -> MAARIV.id
            "לאשה" in text || "לאישה" in text -> LAISHA.id
            else -> null
        }
        return stable[id]?:GENERIC
    }
}