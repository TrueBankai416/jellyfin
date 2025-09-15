using MediaBrowser.Model.Plugins;

namespace Jellyfin.Plugin.MissingEpisodeAlert.Configuration;

/// <summary>
/// Plugin configuration options.
/// </summary>
public class PluginConfiguration : BasePluginConfiguration
{
    /// <summary>
    /// Initializes a new instance of the <see cref="PluginConfiguration"/> class.
    /// </summary>
    public PluginConfiguration()
    {
        // Set default options
        EnablePlugin = true;
        ShowNotificationPopup = true;
        NotificationDurationSeconds = 10;
        CheckOnlyTvShows = true;
        PreventAutoPlay = true;
    }

    /// <summary>
    /// Gets or sets a value indicating whether the plugin is enabled.
    /// </summary>
    public bool EnablePlugin { get; set; }

    /// <summary>
    /// Gets or sets a value indicating whether to show notification popup.
    /// </summary>
    public bool ShowNotificationPopup { get; set; }

    /// <summary>
    /// Gets or sets the notification duration in seconds.
    /// </summary>
    public int NotificationDurationSeconds { get; set; }

    /// <summary>
    /// Gets or sets a value indicating whether to check only TV shows (not movies).
    /// </summary>
    public bool CheckOnlyTvShows { get; set; }

    /// <summary>
    /// Gets or sets a value indicating whether to prevent auto-play when next episode is missing.
    /// </summary>
    public bool PreventAutoPlay { get; set; }
}
