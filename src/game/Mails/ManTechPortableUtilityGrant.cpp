/*
 * This file is part of the CMaNGOS Project. See AUTHORS file for Copyright information
 */

#include "Mails/ManTechPortableUtilityGrant.h"
#include "Mails/Mail.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Item.h"
#include "Entities/Player.h"
#include "Globals/ObjectMgr.h"
#include "Log/Log.h"

#ifdef ENABLE_PLAYERBOTS
#include "playerbot/PlayerbotAIConfig.h"
#endif

namespace
{
    uint32 const PORTABLE_MAILBOX_ITEM = 65000;
    uint32 const PORTABLE_REPAIR_ITEM = 65001;
    char const* PORTABLE_UTILITIES_GRANT = "portable_utilities_v1";

    bool HasGrant(uint32 guid)
    {
        return CharacterDatabase.PQuery("SELECT 1 FROM mantech_character_grants WHERE guid='%u' AND grant_key='%s' LIMIT 1", guid, PORTABLE_UTILITIES_GRANT) != nullptr;
    }

    bool IsBotAccount(uint32 accountId)
    {
#ifdef ENABLE_PLAYERBOTS
        return sPlayerbotAIConfig.IsInRandomAccountList(accountId);
#else
        return false;
#endif
    }

    bool IsEligibleCharacter(uint32 guid)
    {
        auto result = CharacterDatabase.PQuery("SELECT account FROM characters WHERE guid='%u' AND account<>0 AND deleteDate IS NULL", guid);
        if (!result)
            return false;

        return !IsBotAccount(result->Fetch()[0].GetUInt32());
    }
}

bool ManTechPortableUtilityGrant::GrantToCharacter(ObjectGuid characterGuid, Player* onlinePlayer)
{
    if (onlinePlayer && onlinePlayer->GetObjectGuid() != characterGuid)
        return false;

    uint32 guid = characterGuid.GetCounter();
    if (!IsEligibleCharacter(guid) || HasGrant(guid))
        return false;

    Item* mailboxItem = Item::CreateItem(PORTABLE_MAILBOX_ITEM, 1, onlinePlayer);
    Item* repairItem = Item::CreateItem(PORTABLE_REPAIR_ITEM, 1, onlinePlayer);
    if (!mailboxItem || !repairItem)
    {
        delete mailboxItem;
        delete repairItem;
        sLog.outError("ManTech portable utility grant: could not create both utility items for character %u", guid);
        return false;
    }

    MailDraft draft("ManTech Portable Utilities - Independent 30 Minute Cooldowns");
    draft.AddItem(mailboxItem).AddItem(repairItem).SetGrantKey(PORTABLE_UTILITIES_GRANT).SendMailTo(
        MailReceiver(onlinePlayer, characterGuid),
            MailSender(MAIL_NORMAL, uint32(0), MAIL_STATIONERY_GM),
        MAIL_CHECK_MASK_NONE);

    return true;
}

void ManTechPortableUtilityGrant::BackfillExistingCharacters()
{
    auto result = CharacterDatabase.Query(
        "SELECT c.guid, c.account FROM characters c "
        "WHERE c.account<>0 AND c.deleteDate IS NULL "
        "AND NOT EXISTS (SELECT 1 FROM mantech_character_grants g WHERE g.guid=c.guid AND g.grant_key='portable_utilities_v1')");

    if (!result)
    {
        sLog.outString("ManTech portable utility grants: no existing characters require mail.");
        return;
    }

    uint32 grantedCharacters = 0;
    do
    {
        Field* fields = result->Fetch();
        if (IsBotAccount(fields[1].GetUInt32()))
            continue;

        ObjectGuid characterGuid(HIGHGUID_PLAYER, fields[0].GetUInt32());
        if (GrantToCharacter(characterGuid))
            ++grantedCharacters;
    }
    while (result->NextRow());

    sLog.outString("ManTech portable utility grants: mailed %u existing non-bot character(s).", grantedCharacters);
}
