module.exports = async function handler(req, res) {
    if (req.method !== "GET") {
        return res.status(405).json({
            ok: false,
            error: "Method not allowed"
        });
    }

    const key = req.query.key || "";

    if (!process.env.SETUP_KEY ||
        key !== process.env.SETUP_KEY) {
        return res.status(403).json({
            ok: false,
            error: "Unauthorized"
        });
    }

    try {
        const params = new URLSearchParams({
            url: "https://instagram-profile-bot-five.vercel.app/api/webhook",
            secret_token: process.env.WEBHOOK_SECRET
        });

        const response = await fetch(
            `https://api.telegram.org/bot${process.env.BOT_TOKEN}/setWebhook`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: params.toString()
            }
        );

        const result = await response.json();

        return res.status(response.ok ? 200 : 502).json(result);

    } catch (error) {
        return res.status(500).json({
            ok: false,
            error: error.message
        });
    }
};
