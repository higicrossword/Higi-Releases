package com.example.hebrewcrossword

/** Fast, pure admin-only selection over stable catalogue IDs (no I/O). */
object AdminLibrarySeriesFilterV202 {
    const val ALL="ALL"
    const val YEDIOTH="YEDIOTH_DEKEL_BOTH"
    const val TARTEY="TARTEY_DEKEL"
    const val HAFUCH="HAFUCH_DEKEL"
    const val MAARIV="MAARIV_ODED_ROZEN"
    const val GUEST="GUEST_AVISHAI"

    data class Option(val id:String,val title:String)
    val options=listOf(
        Option(ALL,"\u05d4\u05db\u05d5\u05dc"),
        Option(YEDIOTH,"\u05d3\u05e7\u05dc \u05d1\u05e0\u05d5 \u05e9\u05e0\u05d9 \u05d5\u05e8\u05d1\u05d9\u05e2\u05d9"),
        Option(TARTEY,"\u05ea\u05e8\u05ea\u05d9 \u05de\u05e9\u05de\u05e2"),
        Option(HAFUCH,"\u05d4\u05e4\u05d5\u05da \u05e2\u05dc \u05d4\u05e4\u05d5\u05da"),
        Option(MAARIV,"\u05de\u05e2\u05e8\u05d9\u05d1 - \u05e2\u05d5\u05d3\u05d3 \u05e8\u05d5\u05d6\u05df"),
        Option(GUEST,"\u05de\u05e2\u05e8\u05d9\u05d1 \u05d0\u05d5\u05e8\u05d7")
    )
    fun normalized(id:String?):String = id?.takeIf{value->options.any{it.id==value}} ?: ALL
    fun matches(selected:String, seriesId:String?):Boolean = when(normalized(selected)) {
        ALL->true
        YEDIOTH->seriesId=="YEDIOTH_MONDAY_DEKEL" || seriesId=="YEDIOTH_WEDNESDAY_DEKEL"
        else->seriesId==selected
    }
}