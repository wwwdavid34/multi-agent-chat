// All 78 Tarot cards - Rider-Waite-Smith deck (public domain)
// Card images sourced from Wikimedia Commons (public domain, originally published 1909)
// Image base URL from sacred-texts.com (public domain Rider-Waite-Smith scans)

const IMAGE_BASE = 'https://www.sacred-texts.com/tarot/pkt/img/';

const TAROT_DECK = [
    // ========== MAJOR ARCANA (0-21) ==========
    {
        name: "The Fool",
        numeral: "0",
        image: IMAGE_BASE + "ar00.jpg",
        symbol: "\u{1F0A0}",
        upright: "New beginnings, innocence, spontaneity, free spirit. A leap of faith into the unknown with optimism and trust.",
        reversed: "Recklessness, risk-taking, naivety. Holding back due to fear, or rushing in without thinking.",
        suit: "major"
    },
    {
        name: "The Magician",
        numeral: "I",
        image: IMAGE_BASE + "ar01.jpg",
        symbol: "\u2728",
        upright: "Willpower, manifestation, resourcefulness. You have all the tools you need to succeed. Channel your energy with focus.",
        reversed: "Manipulation, poor planning, untapped talents. Trickery or wasted potential.",
        suit: "major"
    },
    {
        name: "The High Priestess",
        numeral: "II",
        image: IMAGE_BASE + "ar02.jpg",
        symbol: "\u{1F319}",
        upright: "Intuition, mystery, inner knowledge. Trust your instincts and look beneath the surface for hidden truths.",
        reversed: "Secrets, withdrawal, silence. Ignoring your intuition or repressing inner wisdom.",
        suit: "major"
    },
    {
        name: "The Empress",
        numeral: "III",
        image: IMAGE_BASE + "ar03.jpg",
        symbol: "\u{1F33F}",
        upright: "Abundance, fertility, nurturing, nature. Creative expression and maternal care bring growth and comfort.",
        reversed: "Dependence, smothering, creative block. Neglecting self-care or being overly controlling.",
        suit: "major"
    },
    {
        name: "The Emperor",
        numeral: "IV",
        image: IMAGE_BASE + "ar04.jpg",
        symbol: "\u{1F451}",
        upright: "Authority, structure, stability, leadership. A solid foundation built through discipline and order.",
        reversed: "Tyranny, rigidity, domination. Excessive control or lack of discipline and structure.",
        suit: "major"
    },
    {
        name: "The Hierophant",
        numeral: "V",
        image: IMAGE_BASE + "ar05.jpg",
        symbol: "\u271E",
        upright: "Tradition, conformity, spiritual wisdom. Seeking guidance from established institutions or mentors.",
        reversed: "Rebellion, subversion, unconventionality. Challenging the status quo or rigid dogma.",
        suit: "major"
    },
    {
        name: "The Lovers",
        numeral: "VI",
        image: IMAGE_BASE + "ar06.jpg",
        symbol: "\u2764",
        upright: "Love, harmony, partnerships, choices. A meaningful connection or important decision guided by the heart.",
        reversed: "Disharmony, imbalance, misalignment. Inner conflict or a relationship out of balance.",
        suit: "major"
    },
    {
        name: "The Chariot",
        numeral: "VII",
        image: IMAGE_BASE + "ar07.jpg",
        symbol: "\u{1F3C6}",
        upright: "Determination, willpower, triumph. Victory through confidence and control over opposing forces.",
        reversed: "Aggression, lack of direction, no control. Obstacles or loss of willpower derailing progress.",
        suit: "major"
    },
    {
        name: "Strength",
        numeral: "VIII",
        image: IMAGE_BASE + "ar08.jpg",
        symbol: "\u{1F981}",
        upright: "Courage, inner strength, compassion, patience. Gentle power and quiet resolve overcome challenges.",
        reversed: "Self-doubt, weakness, insecurity. Raw emotion or inner turmoil undermining your resolve.",
        suit: "major"
    },
    {
        name: "The Hermit",
        numeral: "IX",
        image: IMAGE_BASE + "ar09.jpg",
        symbol: "\u{1F56F}",
        upright: "Soul-searching, introspection, solitude, inner guidance. Withdrawing to find deeper meaning and truth.",
        reversed: "Isolation, loneliness, withdrawal. Excessive solitude or refusing wise counsel.",
        suit: "major"
    },
    {
        name: "Wheel of Fortune",
        numeral: "X",
        image: IMAGE_BASE + "ar10.jpg",
        symbol: "\u2638",
        upright: "Destiny, cycles, turning points, luck. The wheel turns \u2014 change is inevitable and fortune favors the bold.",
        reversed: "Bad luck, resistance to change, broken cycles. Fighting against natural transitions.",
        suit: "major"
    },
    {
        name: "Justice",
        numeral: "XI",
        image: IMAGE_BASE + "ar11.jpg",
        symbol: "\u2696",
        upright: "Fairness, truth, law, cause and effect. Actions have consequences; seek balance and accountability.",
        reversed: "Unfairness, dishonesty, lack of accountability. Avoiding responsibility or biased judgment.",
        suit: "major"
    },
    {
        name: "The Hanged Man",
        numeral: "XII",
        image: IMAGE_BASE + "ar12.jpg",
        symbol: "\u{1F643}",
        upright: "Surrender, letting go, new perspectives. Pause and see the world from a different angle; sacrifice leads to insight.",
        reversed: "Stalling, resistance, indecision. Refusing to let go or unnecessary self-sacrifice.",
        suit: "major"
    },
    {
        name: "Death",
        numeral: "XIII",
        image: IMAGE_BASE + "ar13.jpg",
        symbol: "\u{1F480}",
        upright: "Transformation, endings, transition. Something must end for something new to begin. Embrace profound change.",
        reversed: "Resistance to change, fear of endings, stagnation. Clinging to what no longer serves you.",
        suit: "major"
    },
    {
        name: "Temperance",
        numeral: "XIV",
        image: IMAGE_BASE + "ar14.jpg",
        symbol: "\u{1F54A}",
        upright: "Balance, moderation, patience, harmony. Blending opposites with care creates a greater whole.",
        reversed: "Imbalance, excess, lack of patience. Extremes or forcing things rather than allowing flow.",
        suit: "major"
    },
    {
        name: "The Devil",
        numeral: "XV",
        image: IMAGE_BASE + "ar15.jpg",
        symbol: "\u{1F608}",
        upright: "Bondage, materialism, shadow self. Unhealthy attachments or addictions that hold you captive.",
        reversed: "Release, breaking free, reclaiming power. Overcoming addiction or toxic patterns.",
        suit: "major"
    },
    {
        name: "The Tower",
        numeral: "XVI",
        image: IMAGE_BASE + "ar16.jpg",
        symbol: "\u26A1",
        upright: "Sudden upheaval, revelation, chaos. Destruction of false structures makes way for truth and rebuilding.",
        reversed: "Averting disaster, fear of change, delayed upheaval. Resisting necessary destruction.",
        suit: "major"
    },
    {
        name: "The Star",
        numeral: "XVII",
        image: IMAGE_BASE + "ar17.jpg",
        symbol: "\u2B50",
        upright: "Hope, inspiration, serenity, renewal. After darkness comes light; trust in the universe and heal.",
        reversed: "Despair, disconnection, lack of faith. Losing hope or feeling spiritually empty.",
        suit: "major"
    },
    {
        name: "The Moon",
        numeral: "XVIII",
        image: IMAGE_BASE + "ar18.jpg",
        symbol: "\u{1F315}",
        upright: "Illusion, intuition, the unconscious, fear. Not everything is as it seems; navigate uncertainty with inner knowing.",
        reversed: "Clarity, release of fear, truth revealed. Overcoming confusion and seeing past deception.",
        suit: "major"
    },
    {
        name: "The Sun",
        numeral: "XIX",
        image: IMAGE_BASE + "ar19.jpg",
        symbol: "\u2600",
        upright: "Joy, success, vitality, warmth. Radiant positivity, clarity, and achievement. Everything is coming together.",
        reversed: "Temporary sadness, overly optimistic, lack of clarity. Dimmed joy or unrealistic expectations.",
        suit: "major"
    },
    {
        name: "Judgement",
        numeral: "XX",
        image: IMAGE_BASE + "ar20.jpg",
        symbol: "\u{1F4EF}",
        upright: "Rebirth, inner calling, absolution. A moment of reckoning and spiritual awakening; heed the call.",
        reversed: "Self-doubt, refusal of self-examination. Ignoring your calling or harsh self-judgment.",
        suit: "major"
    },
    {
        name: "The World",
        numeral: "XXI",
        image: IMAGE_BASE + "ar21.jpg",
        symbol: "\u{1F30D}",
        upright: "Completion, accomplishment, wholeness, travel. A cycle fulfilled; celebrate your achievements and integration.",
        reversed: "Incompletion, shortcuts, delays. Falling short of a goal or lacking closure.",
        suit: "major"
    },

    // ========== WANDS (Ace - King) ==========
    {
        name: "Ace of Wands",
        image: IMAGE_BASE + "waac.jpg",
        symbol: "\u{1F525}",
        upright: "Inspiration, creative spark, new initiative. A burst of energy and passion ignites a fresh venture.",
        reversed: "Delays, lack of motivation, hesitation. A creative block or missed opportunity.",
        suit: "wands"
    },
    {
        name: "Two of Wands",
        image: IMAGE_BASE + "wa02.jpg",
        symbol: "\u{1F525}",
        upright: "Planning, future vision, decisions. Standing at the crossroads with the world in your hands.",
        reversed: "Fear of the unknown, lack of planning. Playing it safe when boldness is needed.",
        suit: "wands"
    },
    {
        name: "Three of Wands",
        image: IMAGE_BASE + "wa03.jpg",
        symbol: "\u{1F525}",
        upright: "Expansion, foresight, overseas opportunities. Your plans are taking shape; look to the horizon.",
        reversed: "Delays in plans, frustration, obstacles. Lack of foresight or unreturned efforts.",
        suit: "wands"
    },
    {
        name: "Four of Wands",
        image: IMAGE_BASE + "wa04.jpg",
        symbol: "\u{1F525}",
        upright: "Celebration, harmony, homecoming. A joyful milestone, community, and a sense of belonging.",
        reversed: "Lack of harmony, transition, feeling unwelcome. Disruption in celebrations or instability at home.",
        suit: "wands"
    },
    {
        name: "Five of Wands",
        image: IMAGE_BASE + "wa05.jpg",
        symbol: "\u{1F525}",
        upright: "Conflict, competition, disagreements. Healthy rivalry or chaotic clashing of ideas and egos.",
        reversed: "Avoiding conflict, inner tension, resolution. Finding common ground or suppressing disagreements.",
        suit: "wands"
    },
    {
        name: "Six of Wands",
        image: IMAGE_BASE + "wa06.jpg",
        symbol: "\u{1F525}",
        upright: "Victory, recognition, public acclaim. Success and triumph; others celebrate your achievements.",
        reversed: "Ego, fall from grace, lack of recognition. Arrogance or achievements going unnoticed.",
        suit: "wands"
    },
    {
        name: "Seven of Wands",
        image: IMAGE_BASE + "wa07.jpg",
        symbol: "\u{1F525}",
        upright: "Perseverance, defensiveness, standing your ground. Hold your position against challenges with courage.",
        reversed: "Giving up, overwhelmed, yielding. Feeling besieged and unable to defend your stance.",
        suit: "wands"
    },
    {
        name: "Eight of Wands",
        image: IMAGE_BASE + "wa08.jpg",
        symbol: "\u{1F525}",
        upright: "Swift action, movement, rapid progress. Things are moving fast; ride the momentum forward.",
        reversed: "Delays, frustration, slowdown. Waiting or losing momentum at a critical time.",
        suit: "wands"
    },
    {
        name: "Nine of Wands",
        image: IMAGE_BASE + "wa09.jpg",
        symbol: "\u{1F525}",
        upright: "Resilience, persistence, last stand. Battered but not broken; summon your remaining strength.",
        reversed: "Exhaustion, giving up, paranoia. Pushing too hard or being overly defensive.",
        suit: "wands"
    },
    {
        name: "Ten of Wands",
        image: IMAGE_BASE + "wa10.jpg",
        symbol: "\u{1F525}",
        upright: "Burden, responsibility, hard work. Carrying a heavy load; consider delegating or prioritizing.",
        reversed: "Release of burden, delegation, breakdown. Letting go of what weighs you down.",
        suit: "wands"
    },
    {
        name: "Page of Wands",
        image: IMAGE_BASE + "wapa.jpg",
        symbol: "\u{1F525}",
        upright: "Enthusiasm, exploration, discovery. A curious spirit eager to embark on a new adventure.",
        reversed: "Setbacks, lack of direction, procrastination. Scattered energy or unfocused enthusiasm.",
        suit: "wands"
    },
    {
        name: "Knight of Wands",
        image: IMAGE_BASE + "wakn.jpg",
        symbol: "\u{1F525}",
        upright: "Energy, passion, adventure, impulsiveness. Charging ahead with fiery determination and confidence.",
        reversed: "Haste, scattered energy, delays in travel. Reckless action or burnout from overexertion.",
        suit: "wands"
    },
    {
        name: "Queen of Wands",
        image: IMAGE_BASE + "waqu.jpg",
        symbol: "\u{1F525}",
        upright: "Courage, confidence, determination, warmth. A vibrant leader who inspires others with charisma.",
        reversed: "Selfishness, jealousy, demanding. Overbearing temperament or fading confidence.",
        suit: "wands"
    },
    {
        name: "King of Wands",
        image: IMAGE_BASE + "waki.jpg",
        symbol: "\u{1F525}",
        upright: "Bold leadership, vision, entrepreneur. A natural leader with big ideas and the will to see them through.",
        reversed: "Impulsiveness, ruthlessness, high expectations. Tyrannical leadership or poorly executed vision.",
        suit: "wands"
    },

    // ========== CUPS (Ace - King) ==========
    {
        name: "Ace of Cups",
        image: IMAGE_BASE + "cuac.jpg",
        symbol: "\u{1F499}",
        upright: "New love, compassion, emotional awakening. An overflowing of feelings and deep spiritual connection.",
        reversed: "Emotional loss, blocked feelings, emptiness. Repressed emotions or love withheld.",
        suit: "cups"
    },
    {
        name: "Two of Cups",
        image: IMAGE_BASE + "cu02.jpg",
        symbol: "\u{1F499}",
        upright: "Partnership, unity, mutual attraction. A deep bond forming between two kindred souls.",
        reversed: "Imbalance, broken communication, separation. A relationship out of sync or a rift forming.",
        suit: "cups"
    },
    {
        name: "Three of Cups",
        image: IMAGE_BASE + "cu03.jpg",
        symbol: "\u{1F499}",
        upright: "Celebration, friendship, community. Joyful gatherings and the warmth of close companions.",
        reversed: "Overindulgence, gossip, isolation. Social excess or feeling left out of the group.",
        suit: "cups"
    },
    {
        name: "Four of Cups",
        image: IMAGE_BASE + "cu04.jpg",
        symbol: "\u{1F499}",
        upright: "Apathy, contemplation, missed opportunity. Feeling dissatisfied or failing to see the gift before you.",
        reversed: "Motivation renewed, awareness, seizing opportunity. Snapping out of complacency.",
        suit: "cups"
    },
    {
        name: "Five of Cups",
        image: IMAGE_BASE + "cu05.jpg",
        symbol: "\u{1F499}",
        upright: "Loss, grief, regret. Mourning what has spilled, but two cups still stand behind you.",
        reversed: "Acceptance, moving on, finding peace. Releasing grief and embracing what remains.",
        suit: "cups"
    },
    {
        name: "Six of Cups",
        image: IMAGE_BASE + "cu06.jpg",
        symbol: "\u{1F499}",
        upright: "Nostalgia, childhood memories, innocence. A return to simpler times or reconnecting with the past.",
        reversed: "Living in the past, unrealistic memories, moving forward. Letting go of what was.",
        suit: "cups"
    },
    {
        name: "Seven of Cups",
        image: IMAGE_BASE + "cu07.jpg",
        symbol: "\u{1F499}",
        upright: "Fantasy, illusion, wishful thinking, choices. Many options appear but not all are real; discern carefully.",
        reversed: "Clarity, focus, making a choice. Cutting through illusion to pursue what truly matters.",
        suit: "cups"
    },
    {
        name: "Eight of Cups",
        image: IMAGE_BASE + "cu08.jpg",
        symbol: "\u{1F499}",
        upright: "Walking away, disillusionment, seeking deeper meaning. Leaving behind what no longer fulfills you.",
        reversed: "Fear of change, clinging, aimless drifting. Afraid to leave comfort behind.",
        suit: "cups"
    },
    {
        name: "Nine of Cups",
        image: IMAGE_BASE + "cu09.jpg",
        symbol: "\u{1F499}",
        upright: "Contentment, satisfaction, wish fulfillment. The 'wish card' \u2014 emotional and material fulfillment.",
        reversed: "Dissatisfaction, greed, materialism. Inner emptiness despite outward abundance.",
        suit: "cups"
    },
    {
        name: "Ten of Cups",
        image: IMAGE_BASE + "cu10.jpg",
        symbol: "\u{1F499}",
        upright: "Harmony, family, happiness, alignment. Emotional bliss, loving relationships, and a happy home.",
        reversed: "Broken family, misalignment, domestic strife. Disrupted harmony or unrealistic family ideals.",
        suit: "cups"
    },
    {
        name: "Page of Cups",
        image: IMAGE_BASE + "cupa.jpg",
        symbol: "\u{1F499}",
        upright: "Creative spark, intuitive messages, curiosity. A dreamy spirit offering emotional or artistic inspiration.",
        reversed: "Emotional immaturity, creative block, escapism. Unrealistic dreams or emotional manipulation.",
        suit: "cups"
    },
    {
        name: "Knight of Cups",
        image: IMAGE_BASE + "cukn.jpg",
        symbol: "\u{1F499}",
        upright: "Romance, charm, imagination, following the heart. A graceful messenger of love and creative vision.",
        reversed: "Moodiness, unrealistic expectations, jealousy. Overidealized romance or emotional turbulence.",
        suit: "cups"
    },
    {
        name: "Queen of Cups",
        image: IMAGE_BASE + "cuqu.jpg",
        symbol: "\u{1F499}",
        upright: "Compassion, calm, emotional security. A nurturing soul who feels deeply and offers healing presence.",
        reversed: "Emotional insecurity, codependency, martyrdom. Overwhelmed by others' emotions or self-neglect.",
        suit: "cups"
    },
    {
        name: "King of Cups",
        image: IMAGE_BASE + "cuki.jpg",
        symbol: "\u{1F499}",
        upright: "Emotional balance, diplomacy, wisdom. Mastery of feelings; calm authority with compassionate leadership.",
        reversed: "Emotional manipulation, moodiness, coldness. Using emotional intelligence for selfish ends.",
        suit: "cups"
    },

    // ========== SWORDS (Ace - King) ==========
    {
        name: "Ace of Swords",
        image: IMAGE_BASE + "swac.jpg",
        symbol: "\u2694",
        upright: "Clarity, breakthrough, new ideas. A flash of insight cuts through confusion with piercing truth.",
        reversed: "Confusion, chaos, lack of clarity. Muddled thinking or a truth too painful to face.",
        suit: "swords"
    },
    {
        name: "Two of Swords",
        image: IMAGE_BASE + "sw02.jpg",
        symbol: "\u2694",
        upright: "Indecision, stalemate, difficult choices. A crossroads where avoidance only delays the inevitable.",
        reversed: "Overwhelm, information overload, lesser of two evils. Being forced into a decision.",
        suit: "swords"
    },
    {
        name: "Three of Swords",
        image: IMAGE_BASE + "sw03.jpg",
        symbol: "\u2694",
        upright: "Heartbreak, sorrow, grief. Painful truths, betrayal, or emotional wounds that must be felt to heal.",
        reversed: "Recovery, forgiveness, releasing pain. Beginning to heal from heartache and moving forward.",
        suit: "swords"
    },
    {
        name: "Four of Swords",
        image: IMAGE_BASE + "sw04.jpg",
        symbol: "\u2694",
        upright: "Rest, recovery, contemplation. Retreat and recharge; mental restoration before the next challenge.",
        reversed: "Restlessness, burnout, lack of rest. Pushing yourself too hard without proper recovery.",
        suit: "swords"
    },
    {
        name: "Five of Swords",
        image: IMAGE_BASE + "sw05.jpg",
        symbol: "\u2694",
        upright: "Conflict, defeat, winning at a cost. A hollow victory that leaves bitterness in its wake.",
        reversed: "Reconciliation, making amends, past resentment. Choosing to end a painful conflict.",
        suit: "swords"
    },
    {
        name: "Six of Swords",
        image: IMAGE_BASE + "sw06.jpg",
        symbol: "\u2694",
        upright: "Transition, moving on, calmer waters. Leaving troubled times behind for a more peaceful shore.",
        reversed: "Stuck, resistance to change, unfinished business. Unable or unwilling to move forward.",
        suit: "swords"
    },
    {
        name: "Seven of Swords",
        image: IMAGE_BASE + "sw07.jpg",
        symbol: "\u2694",
        upright: "Deception, strategy, stealth. Acting behind the scenes; be wary of cunning moves by yourself or others.",
        reversed: "Confession, coming clean, conscience. The truth surfaces or a desire to make things right.",
        suit: "swords"
    },
    {
        name: "Eight of Swords",
        image: IMAGE_BASE + "sw08.jpg",
        symbol: "\u2694",
        upright: "Restriction, trapped, self-imposed limitation. Feeling stuck, but the bindings are looser than you think.",
        reversed: "Freedom, release, new perspective. Breaking free from mental prison and self-doubt.",
        suit: "swords"
    },
    {
        name: "Nine of Swords",
        image: IMAGE_BASE + "sw09.jpg",
        symbol: "\u2694",
        upright: "Anxiety, worry, nightmares. Sleepless nights and spiraling fears; the mind as its own worst enemy.",
        reversed: "Hope, reaching out, overcoming fear. Light at the end of the tunnel; worst fears unrealized.",
        suit: "swords"
    },
    {
        name: "Ten of Swords",
        image: IMAGE_BASE + "sw10.jpg",
        symbol: "\u2694",
        upright: "Painful ending, deep wounds, betrayal. Rock bottom; but the only way from here is up.",
        reversed: "Recovery, regeneration, resisting an inevitable end. Rising from the ashes of defeat.",
        suit: "swords"
    },
    {
        name: "Page of Swords",
        image: IMAGE_BASE + "swpa.jpg",
        symbol: "\u2694",
        upright: "Curiosity, mental agility, new ideas. A sharp mind eager to learn and communicate with enthusiasm.",
        reversed: "Deception, manipulation, all talk. Gossip, broken promises, or using words as weapons.",
        suit: "swords"
    },
    {
        name: "Knight of Swords",
        image: IMAGE_BASE + "swkn.jpg",
        symbol: "\u2694",
        upright: "Ambition, fast action, driven. Charging forward with determination and intellectual force.",
        reversed: "Impulsive, no direction, burnout. Acting without thinking or leaving destruction in your wake.",
        suit: "swords"
    },
    {
        name: "Queen of Swords",
        image: IMAGE_BASE + "swqu.jpg",
        symbol: "\u2694",
        upright: "Clear thinking, independence, direct communication. Perceptive truth delivered with grace and honesty.",
        reversed: "Coldness, cruelty, bitterness. Harsh judgment or using intellect to wound rather than heal.",
        suit: "swords"
    },
    {
        name: "King of Swords",
        image: IMAGE_BASE + "swki.jpg",
        symbol: "\u2694",
        upright: "Intellectual authority, truth, clear thinking. A fair and analytical mind that rules with logic and ethics.",
        reversed: "Manipulative, tyrannical, misuse of power. Abusing authority or cold, calculated cruelty.",
        suit: "swords"
    },

    // ========== PENTACLES (Ace - King) ==========
    {
        name: "Ace of Pentacles",
        image: IMAGE_BASE + "peac.jpg",
        symbol: "\u{1FA99}",
        upright: "New financial opportunity, prosperity, manifestation. A seed of material abundance is planted.",
        reversed: "Missed opportunity, lack of planning, scarcity. A promising start that fizzles or poor financial choices.",
        suit: "pentacles"
    },
    {
        name: "Two of Pentacles",
        image: IMAGE_BASE + "pe02.jpg",
        symbol: "\u{1FA99}",
        upright: "Balance, adaptability, juggling priorities. Managing multiple responsibilities with flexibility and grace.",
        reversed: "Imbalance, overwhelm, disorganization. Dropping the ball on important commitments.",
        suit: "pentacles"
    },
    {
        name: "Three of Pentacles",
        image: IMAGE_BASE + "pe03.jpg",
        symbol: "\u{1FA99}",
        upright: "Teamwork, collaboration, skilled work. Mastery through cooperation; your craft is recognized and valued.",
        reversed: "Lack of teamwork, disregard for skills, mediocrity. Poor collaboration or undervalued work.",
        suit: "pentacles"
    },
    {
        name: "Four of Pentacles",
        image: IMAGE_BASE + "pe04.jpg",
        symbol: "\u{1FA99}",
        upright: "Security, control, conservation. Holding tightly to what you have; stability through careful management.",
        reversed: "Greed, materialism, letting go. Clinging too tightly or learning to release control.",
        suit: "pentacles"
    },
    {
        name: "Five of Pentacles",
        image: IMAGE_BASE + "pe05.jpg",
        symbol: "\u{1FA99}",
        upright: "Hardship, financial loss, isolation. Difficult times and feeling left out in the cold; help is near if you seek it.",
        reversed: "Recovery, spiritual growth, end of hardship. The worst is over; warmth and help arrive.",
        suit: "pentacles"
    },
    {
        name: "Six of Pentacles",
        image: IMAGE_BASE + "pe06.jpg",
        symbol: "\u{1FA99}",
        upright: "Generosity, charity, sharing wealth. Giving and receiving in balance; prosperity flows both ways.",
        reversed: "Debt, selfishness, strings attached. Generosity with hidden motives or financial imbalance.",
        suit: "pentacles"
    },
    {
        name: "Seven of Pentacles",
        image: IMAGE_BASE + "pe07.jpg",
        symbol: "\u{1FA99}",
        upright: "Patience, long-term view, investment. Assessing progress; your efforts will bear fruit in time.",
        reversed: "Impatience, poor returns, wasted effort. Frustration over slow progress or bad investment.",
        suit: "pentacles"
    },
    {
        name: "Eight of Pentacles",
        image: IMAGE_BASE + "pe08.jpg",
        symbol: "\u{1FA99}",
        upright: "Diligence, skill development, craftsmanship. Dedicated practice and attention to detail build mastery.",
        reversed: "Perfectionism, lack of motivation, shortcuts. Cutting corners or obsessing over minor details.",
        suit: "pentacles"
    },
    {
        name: "Nine of Pentacles",
        image: IMAGE_BASE + "pe09.jpg",
        symbol: "\u{1FA99}",
        upright: "Luxury, self-sufficiency, financial security. Enjoying the fruits of your labor with grace and independence.",
        reversed: "Over-investment in work, financial setback, superficiality. Material wealth at the cost of deeper fulfillment.",
        suit: "pentacles"
    },
    {
        name: "Ten of Pentacles",
        image: IMAGE_BASE + "pe10.jpg",
        symbol: "\u{1FA99}",
        upright: "Legacy, wealth, family, inheritance. Long-term success, generational stability, and deep roots.",
        reversed: "Financial failure, loss of legacy, family disputes. Instability in long-term plans or family conflict.",
        suit: "pentacles"
    },
    {
        name: "Page of Pentacles",
        image: IMAGE_BASE + "pepa.jpg",
        symbol: "\u{1FA99}",
        upright: "Ambition, desire to learn, new venture. A studious spirit focused on manifesting dreams into reality.",
        reversed: "Lack of progress, procrastination, missed lessons. Failing to follow through on practical goals.",
        suit: "pentacles"
    },
    {
        name: "Knight of Pentacles",
        image: IMAGE_BASE + "pekn.jpg",
        symbol: "\u{1FA99}",
        upright: "Hard work, routine, responsibility. Steady, methodical progress toward a practical goal.",
        reversed: "Boredom, stagnation, laziness. Stuck in a rut or overly cautious to the point of inaction.",
        suit: "pentacles"
    },
    {
        name: "Queen of Pentacles",
        image: IMAGE_BASE + "pequ.jpg",
        symbol: "\u{1FA99}",
        upright: "Nurturing, practical, providing, down-to-earth. Creating comfort and abundance with warmth and care.",
        reversed: "Self-centeredness, jealousy, smothering. Neglecting others or being overly materialistic.",
        suit: "pentacles"
    },
    {
        name: "King of Pentacles",
        image: IMAGE_BASE + "peki.jpg",
        symbol: "\u{1FA99}",
        upright: "Wealth, abundance, security, discipline. A master of the material world who provides stability and prosperity.",
        reversed: "Greed, indulgence, poor financial decisions. Obsession with status or corrupt use of resources.",
        suit: "pentacles"
    }
];
