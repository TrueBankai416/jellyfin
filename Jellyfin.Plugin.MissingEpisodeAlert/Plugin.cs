using System;
using System.Collections.Generic;
using System.Globalization;
using Jellyfin.Plugin.MissingEpisodeAlert.Configuration;
using Jellyfin.Plugin.MissingEpisodeAlert.Services;
using MediaBrowser.Common.Configuration;
using MediaBrowser.Common.Plugins;
using MediaBrowser.Controller.Library;
using MediaBrowser.Controller.Session;
using MediaBrowser.Model.Plugins;
using MediaBrowser.Model.Serialization;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.MissingEpisodeAlert;

/// <summary>
/// The main plugin class for Missing Episode Alert.
/// </summary>
public class Plugin : BasePlugin<PluginConfiguration>, IHasWebPages
{
    private PlaybackMonitorService? _playbackMonitorService;

    /// <summary>
    /// Initializes a new instance of the <see cref="Plugin"/> class.
    /// </summary>
    /// <param name="applicationPaths">Instance of the <see cref="IApplicationPaths"/> interface.</param>
    /// <param name="xmlSerializer">Instance of the <see cref="IXmlSerializer"/> interface.</param>
    public Plugin(IApplicationPaths applicationPaths, IXmlSerializer xmlSerializer)
        : base(applicationPaths, xmlSerializer)
    {
        Instance = this;
    }

    /// <summary>
    /// Initializes the plugin services. This should be called after dependency injection is set up.
    /// </summary>
    /// <param name="serviceProvider">The service provider.</param>
    public void InitializeServices(IServiceProvider serviceProvider)
    {
        try
        {
            var logger = serviceProvider.GetService<ILogger<Plugin>>();
            logger?.LogInformation("Initializing Missing Episode Alert plugin services");

            _playbackMonitorService = serviceProvider.GetService<PlaybackMonitorService>();
            
            logger?.LogInformation("Missing Episode Alert plugin services initialized successfully");
        }
        catch (Exception ex)
        {
            var logger = serviceProvider.GetService<ILogger<Plugin>>();
            logger?.LogError(ex, "Failed to initialize Missing Episode Alert plugin services");
        }
    }

    /// <inheritdoc />
    public override string Name => "Missing Episode Alert";

    /// <inheritdoc />
    public override Guid Id => Guid.Parse("47E5A82C-2D97-4808-A5E3-F6B8B8B8B8B8");

    /// <inheritdoc />
    public override string Description => "Alerts users when the next episode in a series is missing from the library and prevents auto-play.";

    /// <summary>
    /// Gets the current plugin instance.
    /// </summary>
    public static Plugin? Instance { get; private set; }

    /// <inheritdoc />
    public IEnumerable<PluginPageInfo> GetPages()
    {
        return new[]
        {
            new PluginPageInfo
            {
                Name = this.Name,
                EmbeddedResourcePath = string.Format(CultureInfo.InvariantCulture, "{0}.Configuration.configPage.html", GetType().Namespace)
            }
        };
    }

    /// <summary>
    /// Disposes the plugin resources.
    /// </summary>
    public void DisposeServices()
    {
        _playbackMonitorService?.Dispose();
    }
}
